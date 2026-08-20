// Command producer polls Binance's public ticker API for a fixed set of
// assets and streams each price observation onto the "crypto_prices" Kafka
// topic — the ingestion entrypoint for the CryptoPulse pipeline.
//
// This replaces the original Python producer (producer/producer.py), which
// made one batched HTTP call for all assets every 10 seconds. Here, each
// asset gets its own goroutine polling independently on its own 10s cadence
// and feeding a single shared Kafka writer: a slow or failing response for
// one symbol never delays or blocks the others, and every stream can be
// reasoned about (and, if needed, rate-limited or backed off) on its own.
//
// The wire format on the topic is unchanged — same field names, same
// types — so every downstream reader (the Spark structured-streaming job,
// the MinIO archival consumer) keeps working without modification.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"github.com/segmentio/kafka-go"
)

const (
	binanceTickerURL = "https://api.binance.com/api/v3/ticker/24hr"
	kafkaTopic        = "crypto_prices"
	pollInterval      = 10 * time.Second
	httpTimeout       = 10 * time.Second
	kafkaWriteTimeout = 5 * time.Second
)

// Same 15 assets the Python producer tracked.
var coins = []string{
	"BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT",
	"XRPUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
	"DOTUSDT", "LTCUSDT", "SHIBUSDT", "TRXUSDT", "UNIUSDT",
}

// tickerResponse is the subset of Binance's /ticker/24hr response we need.
// Binance returns numeric fields as JSON strings, hence string here and an
// explicit parse below rather than decoding straight into float64.
type tickerResponse struct {
	Symbol             string `json:"symbol"`
	LastPrice          string `json:"lastPrice"`
	QuoteVolume        string `json:"quoteVolume"`
	PriceChangePercent string `json:"priceChangePercent"`
}

// event is the exact JSON shape published to Kafka. Field names and types
// must stay in lockstep with the readers of this topic: streaming/spark_stream.py
// (schema: asset string, price_usd double, volume_24h double,
// change_24h_pct double, event_time double) and producer/simple_consumer.py.
type event struct {
	Asset        string  `json:"asset"`
	PriceUSD     float64 `json:"price_usd"`
	Volume24h    float64 `json:"volume_24h"`
	Change24hPct float64 `json:"change_24h_pct"`
	EventTime    float64 `json:"event_time"`
}

func main() {
	kafkaHost := getEnv("KAFKA_BOOTSTRAP", "localhost:9092")

	writer := &kafka.Writer{
		Addr:         kafka.TCP(kafkaHost),
		Topic:        kafkaTopic,
		Balancer:     &kafka.LeastBytes{},
		BatchTimeout: 250 * time.Millisecond,
		RequiredAcks: kafka.RequireOne,
	}
	defer writer.Close()

	httpClient := &http.Client{Timeout: httpTimeout}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	log.Printf("starting producer: %d assets -> kafka topic %q (%s)", len(coins), kafkaTopic, kafkaHost)

	var wg sync.WaitGroup
	for i, symbol := range coins {
		wg.Add(1)
		// Spread the 15 streams' start times evenly across one poll
		// interval so they don't all hit Binance in the same instant,
		// every 10 seconds, forever.
		startDelay := time.Duration(i) * (pollInterval / time.Duration(len(coins)))
		go func(symbol string, startDelay time.Duration) {
			defer wg.Done()
			streamAsset(ctx, httpClient, writer, symbol, startDelay)
		}(symbol, startDelay)
	}

	wg.Wait()
	log.Println("producer stopped")
}

// streamAsset polls Binance for a single symbol every pollInterval and
// publishes each reading to Kafka, until ctx is cancelled. It is the unit
// of concurrency: one goroutine per asset stream.
func streamAsset(ctx context.Context, client *http.Client, writer *kafka.Writer, symbol string, startDelay time.Duration) {
	select {
	case <-time.After(startDelay):
	case <-ctx.Done():
		return
	}

	ticker := time.NewTicker(pollInterval)
	defer ticker.Stop()

	fetchAndSend(ctx, client, writer, symbol)
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			fetchAndSend(ctx, client, writer, symbol)
		}
	}
}

// fetchAndSend fetches one price observation and writes it to Kafka,
// logging and swallowing any error so a single bad tick never brings the
// goroutine down — the next tick just tries again.
func fetchAndSend(ctx context.Context, client *http.Client, writer *kafka.Writer, symbol string) {
	e, err := fetchPrice(ctx, client, symbol)
	if err != nil {
		log.Printf("[%s] fetch error: %v", symbol, err)
		return
	}

	payload, err := json.Marshal(e)
	if err != nil {
		log.Printf("[%s] marshal error: %v", symbol, err)
		return
	}

	writeCtx, cancel := context.WithTimeout(ctx, kafkaWriteTimeout)
	defer cancel()
	if err := writer.WriteMessages(writeCtx, kafka.Message{Value: payload}); err != nil {
		log.Printf("[%s] kafka write error: %v", symbol, err)
		return
	}

	log.Printf("sent: %s price=%.4f vol24h=%.2f change=%.2f%%", e.Asset, e.PriceUSD, e.Volume24h, e.Change24hPct)
}

func fetchPrice(ctx context.Context, client *http.Client, symbol string) (*event, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, binanceTickerURL, nil)
	if err != nil {
		return nil, err
	}
	q := req.URL.Query()
	q.Set("symbol", symbol)
	req.URL.RawQuery = q.Encode()

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("binance returned status %d", resp.StatusCode)
	}

	var t tickerResponse
	if err := json.NewDecoder(resp.Body).Decode(&t); err != nil {
		return nil, err
	}

	price, err := strconv.ParseFloat(t.LastPrice, 64)
	if err != nil {
		return nil, fmt.Errorf("parse lastPrice: %w", err)
	}
	volume, err := strconv.ParseFloat(t.QuoteVolume, 64)
	if err != nil {
		return nil, fmt.Errorf("parse quoteVolume: %w", err)
	}
	change, err := strconv.ParseFloat(t.PriceChangePercent, 64)
	if err != nil {
		return nil, fmt.Errorf("parse priceChangePercent: %w", err)
	}

	return &event{
		Asset:        t.Symbol,
		PriceUSD:     price,
		Volume24h:    volume,
		Change24hPct: change,
		EventTime:    float64(time.Now().UnixNano()) / 1e9,
	}, nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
