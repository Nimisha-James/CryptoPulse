"""
FastAPI service exposing the LangChain market intelligence agent.
This is what makes the agent a real backend service, not just a script:
a REST contract, response models, persistence, and independent deployability.
"""
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2

from agent import run_agent

app = FastAPI(title="Crypto Market Intelligence Agent", version="1.0")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=5432,
        dbname="crypto_db", user="dataeng", password="dataeng123"
    )


def ensure_table():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_briefings (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL,
            anomaly_count INTEGER,
            briefing TEXT
        );
    """)
    cur.close()
    conn.close()


class BriefingResponse(BaseModel):
    created_at: datetime
    anomaly_count: int
    briefing: str


@app.on_event("startup")
def startup():
    ensure_table()


@app.post("/briefing", response_model=BriefingResponse)
def generate_briefing():
    """Runs the market intelligence agent and persists the result."""

    try:
        result = run_agent()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")

    created_at = datetime.now(timezone.utc)
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO market_briefings (created_at, anomaly_count, briefing) VALUES (%s, %s, %s)",
        (created_at, len(result["anomalies"]), result["briefing"])
    )
    cur.close()
    conn.close()

    return BriefingResponse(
        created_at=created_at,
        anomaly_count=len(result["anomalies"]),
        briefing=result["briefing"],
    )


@app.get("/briefing/latest", response_model=BriefingResponse)
def latest_briefing():
    """Lets the dashboard fetch the most recent briefing without re-running the agent."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT created_at, anomaly_count, briefing FROM market_briefings ORDER BY created_at DESC LIMIT 1"
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="No briefings generated yet")
    return BriefingResponse(created_at=row[0], anomaly_count=row[1], briefing=row[2])


@app.get("/health")
def health():
    return {"status": "ok"}
