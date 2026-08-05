"""
Multi-step LangGraph agent: fetch data -> detect anomalies -> (conditionally)
search for context -> synthesize a market briefing.

Run this file directly (python agent.py) to test the full graph against
real data before wrapping it in FastAPI.
"""
import os
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun

from tools import get_recent_metrics, get_daily_summary, detect_anomalies

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = os.environ.get("AGENT_MODEL", "llama-3.3-70b-versatile")


class AgentState(TypedDict):
    metrics_summary: str
    anomalies: list
    web_context: Optional[str]
    briefing: str


def get_llm():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — export it or add it to .env")
    return ChatGroq(model=MODEL_NAME, api_key=GROQ_API_KEY, temperature=0.3)


# --------------------------------------------------------------------------
# NODES
# --------------------------------------------------------------------------

def fetch_data_node(state: AgentState) -> AgentState:
    """Pulls live + daily data and detects anomalies via plain Python logic."""
    metrics = get_recent_metrics()
    daily = get_daily_summary()
    anomalies = detect_anomalies(metrics)

    latest_per_asset = metrics.sort_values("window_start").groupby("asset").tail(1)
    summary_lines = [
        f"{row['asset']}: ${row['avg_price']:.4f}, volatility {row['volatility']:.5f}"
        if row["volatility"] is not None else f"{row['asset']}: ${row['avg_price']:.4f}"
        for _, row in latest_per_asset.iterrows()
    ]

    return {
        **state,
        "metrics_summary": "\n".join(summary_lines),
        "anomalies": anomalies,
    }


def route_after_fetch(state: AgentState) -> str:
    """Conditional edge: only search the web if something notable was found."""
    return "web_search" if state["anomalies"] else "synthesize"


def web_search_node(state: AgentState) -> AgentState:
    """Only reached when detect_anomalies() found something worth explaining."""
    search = DuckDuckGoSearchRun()
    queries = [f"{a['asset'].replace('USDT', '')} crypto price news today" for a in state["anomalies"]]
    results = []
    for q in queries[:2]:  # cap to avoid excessive calls
        try:
            results.append(search.run(q))
        except Exception as e:
            results.append(f"(search failed: {e})")
    return {**state, "web_context": "\n\n".join(results)}


def synthesize_node(state: AgentState) -> AgentState:
    """The only node that calls the LLM for generation, not just data movement."""
    llm = get_llm()

    anomaly_text = "\n".join(
        f"- {a['asset']}: {a['type']} ({a['value']:.2f})" for a in state["anomalies"]
    ) or "No significant anomalies detected in the current window."

    context_text = state.get("web_context") or "No external context was needed."

    prompt = f"""You are a market intelligence analyst. Write a short, punchy
briefing (2-4 sentences) in a professional analyst tone. Lead with the
most important anomaly, not a general price rundown. Do not speculate
beyond what the data and search context support...

LIVE METRICS:
{state['metrics_summary']}

DETECTED ANOMALIES:
{anomaly_text}

RELEVANT CONTEXT:
{context_text}
"""
    response = llm.invoke(prompt)
    return {**state, "briefing": response.content}


# --------------------------------------------------------------------------
# GRAPH ASSEMBLY
# --------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("fetch_data")
    graph.add_conditional_edges(
        "fetch_data",
        route_after_fetch,
        {"web_search": "web_search", "synthesize": "synthesize"},
    )
    graph.add_edge("web_search", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"metrics_summary": "", "anomalies": [], "web_context": None, "briefing": ""})
    print("\n--- ANOMALIES ---")
    print(result["anomalies"])
    print("\n--- BRIEFING ---")
    print(result["briefing"])
