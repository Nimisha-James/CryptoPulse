import json
import time
import requests
from kafka import KafkaProducer

import os
KAFKA_HOST = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_HOST,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT",
    "XRPUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
    "DOTUSDT", "LTCUSDT", "SHIBUSDT", "TRXUSDT", "UNIUSDT",
]

def fetch_prices():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbols": json.dumps(COINS, separators=(',', ':'))}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def run():
    print("Starting producer... pushing to topic 'crypto_prices'")
    while True:
        try:
            data = fetch_prices()
            timestamp = time.time()
            for item in data:
                event = {
                    "asset": item["symbol"],
                    "price_usd": float(item["lastPrice"]),
                    "volume_24h": float(item["quoteVolume"]),
                    "change_24h_pct": float(item["priceChangePercent"]),
                    "event_time": timestamp
                }
                producer.send("crypto_prices", value=event)
                print(f"Sent: {event}")
            producer.flush()
        except Exception as e:
            print(f"Error fetching/sending: {e}")
        time.sleep(10)

if __name__ == "__main__":
    run()