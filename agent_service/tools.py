"""
Tools for the market intelligence agent.
Each function here is a discrete, independently-testable unit — run
this file directly (python tools.py) to sanity-check them against your
real database before ever wiring them into the LangGraph agent.
"""
import os
import psycopg2
import pandas as pd

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

# Thresholds for what counts as "notable" — tune these once you see real data.
VOLATILITY_SPIKE_THRESHOLD = 2.0     # absolute volatility value
PRICE_CHANGE_THRESHOLD_PCT = 1.5     # % change within the recent window


def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST, port=5432,
        dbname="crypto_db", user="dataeng", password="dataeng123"
    )


def get_recent_metrics(limit_per_asset: int = 10, assets: list[str] | None = None) -> pd.DataFrame:
    """Pulls the most recent rolling-window rows per asset from live_metrics.
    If `assets` is given, restricts to only those assets — this is what
    makes the agent's briefing respect the dashboard's asset selection
    instead of always analyzing the entire tracked universe."""
    conn = get_connection()
    if assets:
        query = """
            SELECT asset, avg_price, volatility, window_start, window_end
            FROM live_metrics
            WHERE asset = ANY(%s)
            ORDER BY window_start DESC
            LIMIT 500;
        """
        df = pd.read_sql(query, conn, params=(assets,))
    else:
        query = """
            SELECT asset, avg_price, volatility, window_start, window_end
            FROM live_metrics
            ORDER BY window_start DESC
            LIMIT 500;
        """
        df = pd.read_sql(query, conn)
    conn.close()
    if df.empty:
        return df
    return df.sort_values("window_start", ascending=False).groupby("asset").head(limit_per_asset)


def get_daily_summary(assets: list[str] | None = None) -> pd.DataFrame:
    """Pulls the most recent day's OHLC summary per asset, optionally filtered."""
    conn = get_connection()
    if assets:
        query = """
            SELECT asset_id, event_date, open_price, high_price, low_price, close_price, total_volume
            FROM daily_ohlc_summary
            WHERE asset_id = ANY(%s)
            ORDER BY event_date DESC
            LIMIT 100;
        """
        df = pd.read_sql(query, conn, params=(assets,))
    else:
        query = """
            SELECT asset_id, event_date, open_price, high_price, low_price, close_price, total_volume
            FROM daily_ohlc_summary
            ORDER BY event_date DESC
            LIMIT 100;
        """
        df = pd.read_sql(query, conn)
    conn.close()
    return df


def detect_anomalies(metrics_df: pd.DataFrame) -> list[dict]:
    """
    Plain-Python threshold logic — deliberately NOT an LLM call.
    Anomaly detection should be fast, deterministic, and cheap; the LLM's
    job is reasoning about *why* something notable happened, not deciding
    whether something notable happened at all.
    """
    anomalies = []
    if metrics_df.empty:
        return anomalies

    for asset, group in metrics_df.groupby("asset"):
        group = group.sort_values("window_start")
        if len(group) < 2:
            continue

        max_vol = group["volatility"].max()
        if pd.notna(max_vol) and max_vol > VOLATILITY_SPIKE_THRESHOLD:
            anomalies.append({
                "asset": asset,
                "type": "volatility_spike",
                "value": float(max_vol),
            })

        first_price = group["avg_price"].iloc[0]
        last_price = group["avg_price"].iloc[-1]
        if first_price and first_price != 0:
            pct_change = ((last_price - first_price) / first_price) * 100
            if abs(pct_change) > PRICE_CHANGE_THRESHOLD_PCT:
                anomalies.append({
                    "asset": asset,
                    "type": "price_move",
                    "value": float(pct_change),
                })

    return anomalies


if __name__ == "__main__":
    # Quick manual verification — run this file directly before touching LangGraph.
    metrics = get_recent_metrics()
    print(f"Fetched {len(metrics)} recent metric rows")
    print(metrics.head())

    daily = get_daily_summary()
    print(f"\nFetched {len(daily)} daily summary rows")
    print(daily.head())

    found = detect_anomalies(metrics)
    print(f"\nAnomalies detected: {found}")