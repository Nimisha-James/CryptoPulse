"""
Market intelligence pipeline: fetch data -> detect anomalies ->
(conditionally) search for context -> synthesize a market briefing.

Run this file directly (python agent.py) to test the full pipeline against
real data before wrapping it in FastAPI.

Note: this version replaces the previous LangGraph StateGraph implementation
with a plain sequential function. Behavior is preserved: anomalies are
detected first, web search only runs if anomalies were found (capped at 2
queries), and the LLM is called once at the end to synthesize the briefing.
"""
import os
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun

from tools import (
    get_recent_metrics,
    get_daily_summary,
    detect_anomalies,
)

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = os.environ.get("AGENT_MODEL", "llama-3.3-70b-versatile")


def get_llm():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — export it or add it to .env")
    return ChatGroq(
        model=MODEL_NAME,
        api_key=GROQ_API_KEY,
        temperature=0.3
    )


def run_agent():
    """
    Executes the complete market intelligence pipeline.
    """

    metrics = get_recent_metrics()
    daily = get_daily_summary()

    anomalies = detect_anomalies(metrics)

    latest = (
        metrics.sort_values("window_start")
        .groupby("asset")
        .tail(1)
    )

    summary_lines = []

    for _, row in latest.iterrows():

        if row["volatility"] is not None:
            summary_lines.append(
                f"{row['asset']}: ${row['avg_price']:.4f}, "
                f"volatility {row['volatility']:.5f}"
            )
        else:
            summary_lines.append(
                f"{row['asset']}: ${row['avg_price']:.4f}"
            )

    metrics_summary = "\n".join(summary_lines)

    web_context = ""

    if anomalies:

        search = DuckDuckGoSearchRun()

        results = []

        # cap to avoid excessive calls, same as the original web_search_node
        for anomaly in anomalies[:2]:

            query = (
                f"{anomaly['asset'].replace('USDT','')} "
                "crypto price news today"
            )

            try:
                results.append(search.run(query))
            except Exception as e:
                results.append(f"Search failed: {e}")

        web_context = "\n\n".join(results)

    anomaly_text = "\n".join(
        f"- {a['asset']}: {a['type']} ({a['value']:.2f})"
        for a in anomalies
    )

    if not anomaly_text:
        anomaly_text = "No significant anomalies detected."

    if not web_context:
        web_context = "No external context."

    prompt = f"""
You are a crypto market analyst.

Write a concise professional briefing
(2-4 bullet points).

LIVE METRICS
{metrics_summary}

ANOMALIES
{anomaly_text}

WEB CONTEXT
{web_context}
"""

    llm = get_llm()

    response = llm.invoke(prompt)

    return {
        "briefing": response.content,
        "anomalies": anomalies
    }


if __name__ == "__main__":

    result = run_agent()

    print(result["anomalies"])
    print(result["briefing"])