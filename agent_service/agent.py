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
from langchain_anthropic import ChatAnthropic
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv
from tools import (
    get_recent_metrics,
    get_daily_summary,
    detect_anomalies,
)
load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_NAME = os.environ.get("AGENT_MODEL", "claude-sonnet-4-5")  # pick the model id your account has access to


def get_llm():
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — export it or add it to .env")
    return ChatAnthropic(
        model=MODEL_NAME,
        api_key=ANTHROPIC_API_KEY,
        temperature=0.3
    )


def run_agent(assets: list[str] | None = None):
    """
    Executes the complete market intelligence pipeline.

    If `assets` is provided, every stage -- data fetching, anomaly
    detection, and the prompt itself -- is scoped to only those assets,
    so the briefing matches whatever the dashboard's asset selector
    currently has checked rather than always covering the entire
    tracked universe regardless of what's actually displayed.
    """
    metrics = get_recent_metrics(assets=assets)
    daily = get_daily_summary(assets=assets)
    anomalies = detect_anomalies(metrics)

    if metrics.empty:
        return {
            "briefing": "• No data available for the selected assets.",
            "anomalies": [],
        }

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

    scope_line = (
        f"Cover ONLY these assets: {', '.join(assets)}. Do not mention any other cryptocurrency."
        if assets else
        "Cover the full set of tracked assets below."
    )

    prompt = f"""You are a market intelligence analyst. Write a short, punchy
briefing as 2-4 bullet points in a professional analyst tone. Lead with the
most important anomaly, not a general price rundown. Do not speculate
beyond what the data and search context support.

{scope_line}

STRICT OUTPUT FORMAT -- follow this exactly:
- Output ONLY the bullet points. No heading, no intro sentence, no
  "Here's the briefing" preamble, no closing remarks.
- Each bullet must be a single line of plain text starting with "• "
  (a bullet character followed by one space).
- Do NOT use markdown syntax (no "-", "*", "**bold**", numbered lists).
- Put exactly one blank line between bullets.
- Each bullet should be one to two sentences, factual and specific.

LIVE METRICS
{metrics_summary}

ANOMALIES
{anomaly_text}

WEB CONTEXT
{web_context}
"""
    llm = get_llm()
    response = llm.invoke(prompt)
    briefing_text = format_briefing(response.content)
    return {
        "briefing": briefing_text,
        "anomalies": anomalies
    }


def format_briefing(raw_text: str) -> str:
    """
    Normalizes whatever the LLM returned into a clean, consistent bullet
    format: one "• " bullet per line, exactly one blank line between
    bullets, no stray markdown or preamble lines that slipped through.
    """
    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    bullets = []
    for line in lines:
        cleaned = line.lstrip("•-*0123456789. ").strip()
        if cleaned:
            bullets.append(cleaned)
    return "\n\n".join(f"• {b}" for b in bullets)


if __name__ == "__main__":
    result = run_agent()
    print(result["anomalies"])
    print(result["briefing"])