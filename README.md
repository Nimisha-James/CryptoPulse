# CryptoPulse — Real-Time Crypto Market Analytics Pipeline


This project presents an end-to-end data engineering pipeline for real-time and historical cryptocurrency market intelligence. Crypto markets move on timescales from seconds to months, and answering questions at both ends — "what is Bitcoin doing right now" versus "how did Solana trend last month" — requires fundamentally different infrastructure. This project implements both: a **speed layer** built on Kafka and Spark Structured Streaming for live, low-latency metrics, and a **batch layer** built on Airflow and dbt for durable, fully reconciled historical analytics — the classic Lambda architecture pattern, applied deliberately rather than incidentally.

The entire stack — ingestion, streaming, storage, orchestration, transformation, and dashboard — is fully containerized and runs from a single Docker Compose command.

## Features

- **Live Ingestion**: A Go producer runs one goroutine per tracked asset, each independently polling the Binance public market data API every 10 seconds and streaming events through Kafka.
- **Real-Time Metrics**: Spark Structured Streaming computes rolling average price and volatility over a 5-minute sliding window, with watermarking to correctly handle late-arriving data.
- **Durable Historical Archive**: Every raw event is preserved as date-partitioned Parquet files in MinIO (S3-compatible object storage), independent of any downstream transformation.
- **Automated Daily Orchestration**: Airflow loads archived data into the warehouse on a scheduled, retry-aware, dependency-managed DAG.
- **Modeled, Tested Analytics Layer**: dbt transforms raw data into a deduplicated staging layer, a star schema (fact + dimension tables), and a daily OHLC summary table — backed by automated data quality tests.
- **Live + Historical Dashboard**: A Streamlit app surfaces both the real-time rolling metrics and the historical analytical tables in one place.
- **Full Containerization**: All 12+ services (Kafka, Postgres, MinIO, Airflow, Spark, producers/consumers, dashboard) run from a single `docker-compose up`.

## Architecture

```
Binance API ──(15 concurrent goroutines, 10s poll each)──▶ Kafka topic
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                            ▼
              Spark Structured Streaming      Archival Consumer
              (rolling avg + volatility,            │
               5-min sliding window,                ▼
               watermarking)                MinIO (S3-compatible)
                        │                    — raw Parquet, date-
                        ▼                      partitioned
                  Postgres (live metrics)            │
                                                      ▼
                                             Airflow (daily DAG)
                                                      │
                                                      ▼
                                             Postgres staging table
                                                      │
                                                      ▼
                                                    dbt
                                          (dedup → dimension/fact
                                           tables → daily OHLC
                                           summary → data tests)
                                                      │
                                                      ▼
                                          Streamlit Dashboard
```

Everything — ingestion, streaming, archival, orchestration, transformation, and the dashboard — runs as a single Docker Compose stack.

## Tech Stack

| Layer | Technology |
|---|---|
| Market data source | Binance public market data API |
| Message queue | Apache Kafka |
| Stream processing | Apache Spark Structured Streaming |
| Object storage | MinIO (S3-compatible) |
| Storage format | Parquet, Hive-style date partitioning |
| Orchestration | Apache Airflow |
| Transformation & modeling | dbt |
| Database | PostgreSQL |
| Dashboard | Streamlit |
| Containerization | Docker Compose (12+ services) |
| Language | Go, Python, SQL |

## Methodology

### 1. Ingestion
The producer (Go — see `producer-go/`) runs one goroutine per tracked asset, each independently polling Binance's public ticker API every 10 seconds and publishing its own price observation to a Kafka topic. A slow or failing response for one asset never blocks or delays the others, and every stream shares a single Kafka writer. This decouples ingestion from every downstream consumer.

### 2. Real-Time Stream Processing
A Spark Structured Streaming job reads directly from Kafka and computes two rolling metrics per asset — average price and volatility (standard deviation) — over a 5-minute sliding window, recalculated every minute. Watermarking allows events arriving up to 2 minutes late to still be correctly included.

### 3. Historical Storage
Every raw event is independently archived as batched, date-partitioned Parquet files in MinIO (S3-compatible object storage), preserving the full untouched history so any transformation can be reprocessed from source if needed.

### 4. Orchestration
A daily Airflow DAG loads the accumulated raw files from object storage into a Postgres staging table, with automatic retries, explicit dependency ordering, and catch-up runs disabled.

### 5. Transformation & Modeling
dbt builds a layered SQL pipeline on top of staging:

| Layer | Purpose |
|---|---|
| Staging | Deduplication, type-casting, field renaming |
| Dimension table | Descriptive, slowly-changing asset metadata |
| Fact table | Granular, continuously growing price observations |
| Daily summary table | Pre-computed OHLC (open/high/low/close) per asset per day |

Automated dbt tests enforce not-null constraints and fact-to-dimension referential integrity, so the pipeline fails loudly if a data quality issue is introduced.

### 6. Dashboard
A Streamlit app serves both the live rolling metrics and the historical/analytical tables in a single interface.

### 7. Containerization
The full stack — Kafka, Postgres, MinIO, Airflow, Spark, the producer/consumer services, and the dashboard — runs from a single `docker-compose up`, with environment-driven service configuration and automatic restart policies across all 12+ services.


