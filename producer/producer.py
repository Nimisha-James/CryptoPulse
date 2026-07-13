import json
import time
import requests
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

COINS = ["bitcoin", "ethereum", "solana", "dogecoin", "cardano"]

def fetch_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(COINS),
        "vs_currencies": "usd",
        "include_24hr_vol": "true",
        "include_24hr_change": "true"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def run():
    print("Starting producer... pushing to topic 'crypto_prices'")
    while True:
        try:
            data = fetch_prices()
            timestamp = time.time()
            for coin, values in data.items():
                event = {
                    "asset": coin,
                    "price_usd": values.get("usd"),
                    "volume_24h": values.get("usd_24h_vol"),
                    "change_24h_pct": values.get("usd_24h_change"),
                    "event_time": timestamp
                }
                producer.send("crypto_prices", value=event)
                print(f"Sent: {event}")
            producer.flush()
        except Exception as e:
            print(f"Error fetching/sending: {e}")
        time.sleep(10)  # CoinGecko free tier rate limit

if __name__ == "__main__":
    run()
