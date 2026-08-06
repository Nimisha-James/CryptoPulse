"""
Dashboard API: exposes pipeline tables (live_metrics, daily_ohlc_summary)
as REST endpoints for the React frontend. Deliberately separate from
agent-service — this one is pure data serving, no LLM calls.

Each endpoint opens and closes its own short-lived connection rather than
holding one open across requests. This is a deliberate choice: the earlier
Streamlit dashboard's persistent cached connection was what caused the
"aborted transaction poisons every future query" bug documented in this
project's history. A REST API handling low request volume doesn't need
connection pooling to perform well, and a fresh connection per request
makes that entire bug class structurally impossible here.
"""
import os
from datetime import date
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras

app = FastAPI(title="Crypto Pipeline Dashboard API", version="1.0")

# CORS is a fallback safety net — in Docker, nginx same-origin proxying
# means the browser never actually needs it, but this keeps `npm run dev`
# working even if someone bypasses the Vite proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")


def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=5432,
        dbname="crypto_db", user="dataeng", password="dataeng123",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def run_query(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


class LiveMetric(BaseModel):
    asset: str
    avg_price: float
    volatility: Optional[float]
    window_start: str
    window_end: str


class SeriesPoint(BaseModel):
    window_start: str
    avg_price: float


class DailySummary(BaseModel):
    asset_id: str
    event_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    total_volume: float


@app.get("/assets", response_model=list[str])
def get_assets():
    rows = run_query("SELECT DISTINCT asset FROM live_metrics ORDER BY asset;")
    return [r["asset"] for r in rows]


@app.get("/live-metrics", response_model=list[LiveMetric])
def get_live_metrics():
    """Latest rolling-window row per asset — same DISTINCT ON pattern the
    Streamlit dashboard used, since duplicate window rows are expected
    (see this project's notes on outputMode('update') + append writes)."""
    rows = run_query("""
        SELECT DISTINCT ON (asset)
            asset, avg_price, volatility,
            window_start::text, window_end::text
        FROM live_metrics
        ORDER BY asset, window_start DESC, window_end DESC;
    """)
    return rows


@app.get("/live-metrics/series", response_model=list[SeriesPoint])
def get_series(asset: str = Query(...), limit: int = 40):
    """Sparkline data for one asset, correctly ordered chronologically.
    Fetches DESC LIMIT N (the N most recent rows) then reverses in Python —
    fetching ASC LIMIT N would grab the OLDEST N rows instead, a bug this
    project hit once already in the Streamlit version."""
    rows = run_query("""
        SELECT window_start::text, avg_price
        FROM live_metrics
        WHERE asset = %s
        ORDER BY window_start DESC
        LIMIT %s;
    """, (asset, limit))
    return list(reversed(rows))


@app.get("/daily-summary", response_model=list[DailySummary])
def get_daily_summary():
    rows = run_query("""
        SELECT asset_id, event_date, open_price, high_price,
               low_price, close_price, total_volume
        FROM daily_ohlc_summary
        ORDER BY event_date DESC, asset_id ASC;
    """)
    return rows


@app.get("/health")
def health():
    return {"status": "ok"}