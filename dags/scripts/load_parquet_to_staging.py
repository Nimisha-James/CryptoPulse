import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from io import BytesIO
from datetime import datetime
import sys


s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",  # note: container hostname, not localhost
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123"
)

BUCKET = "crypto-raw"
target_date = sys.argv[1]  # passed in by Airflow as the logical date, e.g. "2026-07-14"
prefix = f"date={target_date}/"

conn = psycopg2.connect(
    host="postgres",  # container hostname, not localhost
    port=5432,
    dbname="crypto_db",
    user="dataeng",
    password="dataeng123"
)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_price_ticks (
        asset TEXT,
        price_usd DOUBLE PRECISION,
        volume_24h DOUBLE PRECISION,
        change_24h_pct DOUBLE PRECISION,
        event_time DOUBLE PRECISION
    );
""")

paginator = s3.get_paginator("list_objects_v2")
files = []
for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
    for obj in page.get("Contents", []):
        files.append(obj["Key"])

print(f"Found {len(files)} Parquet files for {target_date}")

all_rows = []
for key in files:
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_parquet(BytesIO(obj["Body"].read()))
    all_rows.extend(df.to_records(index=False).tolist())

if all_rows:
    execute_values(
        cur,
        "INSERT INTO raw_price_ticks (asset, price_usd, volume_24h, change_24h_pct, event_time) VALUES %s",
        all_rows
    )
    conn.commit()
    print(f"Loaded {len(all_rows)} rows into raw_price_ticks")
else:
    print("No rows to load")

cur.close()
conn.close()
