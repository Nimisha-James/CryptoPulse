import json
import boto3
import pandas as pd
from kafka import KafkaConsumer
from io import BytesIO
from datetime import datetime

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123"
)

BUCKET = "crypto-raw"

existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
if BUCKET not in existing:
    s3.create_bucket(Bucket=BUCKET)

consumer = KafkaConsumer(
    "crypto_prices",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest"
)

buffer = []
BATCH_SIZE = 5

def flush_to_parquet():
    global buffer
    if not buffer:
        return
    df = pd.DataFrame(buffer)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"date={today}/batch_{datetime.utcnow().timestamp()}.parquet"
    out_buffer = BytesIO()
    df.to_parquet(out_buffer, index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=out_buffer.getvalue())
    print(f"Flushed {len(buffer)} records to s3://{BUCKET}/{key}")
    buffer = []

print("Consuming and writing to MinIO...")
for message in consumer:
    buffer.append(message.value)
    if len(buffer) >= BATCH_SIZE:
        flush_to_parquet()
