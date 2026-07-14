import json
import boto3
import pandas as pd
from kafka import KafkaConsumer
from io import BytesIO
from datetime import datetime

import os
KAFKA_HOST = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123"
)

consumer = KafkaConsumer(
    "crypto_prices",
    bootstrap_servers=KAFKA_HOST,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest"
)

BUCKET = "crypto-raw"

existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
if BUCKET not in existing:
    s3.create_bucket(Bucket=BUCKET)

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
