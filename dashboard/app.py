"""
Crypto Market Intelligence — Live Dashboard
Reads live_metrics (Spark output) and daily_ohlc_summary (dbt output) from Postgres.
"""
import streamlit as st
import pandas as pd
import psycopg2
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Crypto Market Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# Reruns the whole script every 5 seconds — this is what keeps the clock
# ticking and the data fresh without any manual page refresh.
st_autorefresh(interval=5000, key="auto_refresh_tick")
# ----------------------------------------------------------------------------
# DESIGN TOKENS — dark trading-terminal aesthetic
# ----------------------------------------------------------------------------
BG_PRIMARY   = "#0A0E14"
BG_PANEL     = "#10151C"
BG_PANEL_ALT = "#141B24"
BORDER       = "#1E2630"
TEXT_PRIMARY = "#E6E9EF"
TEXT_MUTED   = "#6B7684"
ACCENT_CYAN  = "#4FD1E8"
ACCENT_GREEN = "#00E5A0"
ACCENT_RED   = "#FF5470"
ACCENT_AMBER = "#FFB454"
# ----------------------------------------------------------------------------
# GLOBAL CSS
# ----------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500&display=swap');
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}
.stApp {{
    background:
        radial-gradient(circle at 15% 0%, rgba(79,209,232,0.06) 0%, transparent 40%),
        radial-gradient(circle at 85% 100%, rgba(0,229,160,0.05) 0%, transparent 40%),
        linear-gradient(180deg, {BG_PRIMARY} 0%, #0C1119 100%);
    color: {TEXT_PRIMARY};
}}
#MainMenu, footer, header {{visibility: hidden;}}
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}}
/* ---------- Header ---------- */
.dash-header {{
    display: flex;
    align-items: center;
    margin-top: -5px;
    height: 40px;
}}
.dash-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.9rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin: 0;
    color: {TEXT_PRIMARY};
    line-height: 40px;
}}
.dash-title span {{ color: {ACCENT_CYAN}; }}

/* live-pill and the refresh button share this exact height, so their
   tops/bottoms line up regardless of how each element sizes its own content */
.live-pill {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    height: 38px;
    min-height: 38px;
    max-height: 38px;
    box-sizing: border-box;
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 999px;
    padding: 0 0.9rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    line-height: 1;
    color: {ACCENT_GREEN};
    letter-spacing: 0.08em;
    white-space: nowrap;
}}
.pulse-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {ACCENT_GREEN};
    box-shadow: 0 0 0 0 rgba(0,229,160,0.6);
    animation: pulse 1.8s infinite;
    flex-shrink: 0;
}}
@keyframes pulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(0,229,160,0.55); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(0,229,160,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(0,229,160,0); }}
}}
/* ---------- Status indicator colors (reused on asset cards) ---------- */
.vol-up   {{ color: {ACCENT_GREEN}; }}
.vol-down {{ color: {ACCENT_RED}; }}
.vol-dot {{
    display: inline-block;
    width: 8px; height: 8px; border-radius: 50%;
    margin-right: 0.35rem;
    vertical-align: middle;
}}
.vol-dot.up   {{ background: {ACCENT_GREEN}; }}
.vol-dot.down {{ background: {ACCENT_RED}; box-shadow: 0 0 6px {ACCENT_RED}66; }}
/* ---------- Section labels ---------- */
.section-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: {ACCENT_CYAN};
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 1.8rem 0 0.7rem 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}
.section-label::after {{
    content: "";
    flex: 1;
    height: 1px;
    background: {BORDER};
}}
/* ---------- Asset cards ---------- */
.asset-card {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1.05rem 1.15rem;
    transition: border-color 0.2s ease;
}}
.asset-card:hover {{ border-color: {ACCENT_CYAN}44; }}
.asset-name {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: {TEXT_MUTED};
    letter-spacing: 0.06em;
}}
.asset-price-row {{
    display: flex;
    align-items: center;
    margin: 0.15rem 0 0.3rem 0;
}}
.asset-price {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}
.asset-vol {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: {TEXT_MUTED};
}}
.asset-vol b {{ font-weight: 600; }}
/* ---------- Dataframe polish ---------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}
.footer-note {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: {TEXT_MUTED};
    text-align: center;
    margin-top: 2.5rem;
    letter-spacing: 0.04em;
}}
/* ---------- Refresh button (native Streamlit button, restyled) ----------
   Streamlit's buttons use baseweb under the hood, which sets its own
   height/padding with strong specificity — everything here is !important
   to guarantee it actually matches .live-pill's box exactly. */
div[data-testid="stButton"] {{
    margin-top: 0 !important;
    display: flex !important;
    align-items: center !important;
    height: 38px !important;
}}
div[data-testid="stButton"] > button {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    box-sizing: border-box !important;
    background: {BG_PANEL} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 999px !important;
    color: {ACCENT_CYAN} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 3rem !important;
    line-height: 1 !important;
    letter-spacing: 0.04em;
    padding: 0 1rem !important;
    margin-top: 1rem;
    transition: border-color 0.2s ease, color 0.2s ease;
}}
div[data-testid="stButton"] > button p {{
    font-size: 0.75rem !important;
    line-height: 1 !important;
    margin: 0 !important;
}}
div[data-testid="stButton"] > button:hover {{
    border-color: {ACCENT_CYAN} !important;
    color: {ACCENT_CYAN} !important;
}}
div[data-testid="stButton"] > button:active {{
    color: {ACCENT_GREEN} !important;
}}
/* Column holding the button gets the same fixed height, so nothing
   inside it (default Streamlit widget spacing, etc.) can push it taller. */
div[data-testid="column"]:has(div[data-testid="stButton"]) {{
    display: flex !important;
    align-items: center !important;
    height: 38px !important;
}}
/* Force the whole header row (title block + pill + button) onto one
   vertically-centered baseline, no matter what Streamlit's own column
   wrapper spacing does. */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) {{
    align-items: center !important;
}}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stButton"]) > div {{
    display: flex !important;
    align-items: center !important;
}}
</style>
""", unsafe_allow_html=True)
# ----------------------------------------------------------------------------
# DB CONNECTION
# ----------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="localhost", port=5432,
        dbname="crypto_db", user="dataeng", password="dataeng123"
    )
@st.cache_data(ttl=10)
def load_latest_metrics():
    conn = get_connection()
    query = """
        SELECT DISTINCT ON (asset)
            asset, avg_price, volatility, window_start, window_end
        FROM live_metrics
        ORDER BY asset, window_start DESC, window_end DESC;
    """
    return pd.read_sql(query, conn)
@st.cache_data(ttl=10)
def load_recent_series(asset, limit=40):
    conn = get_connection()
    query = """
        SELECT window_start, avg_price
        FROM live_metrics
        WHERE asset = %s
        ORDER BY window_start DESC
        LIMIT %s;
    """
    df = pd.read_sql(query, conn, params=(asset, limit))
    return df.sort_values("window_start")
@st.cache_data(ttl=300)
def load_daily_summary():
    conn = get_connection()
    query = """
        SELECT asset_id, event_date, open_price, high_price,
               low_price, close_price, total_volume
        FROM daily_ohlc_summary
        ORDER BY event_date DESC, asset_id ASC;
    """
    return pd.read_sql(query, conn)
# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
header_col, pill_col, button_col = st.columns([8, 1.5, 1])

with header_col:
    st.markdown(f"""
    <div class="dash-header">
        <div class="dash-title">◈ CRYPTO<span>MARKET</span>INTEL</div>
    </div>
    """, unsafe_allow_html=True)
with pill_col:
    st.markdown(f"""
    <div class="live-pill">
        <span class="pulse-dot"></span>
        LIVE · {datetime.now().strftime('%H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)
with button_col:
    if st.button("⟳ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
st.markdown(f"""
    <hr style="
        border: none;
        border-top: 1px solid {BORDER};
        margin-top: 15px;
        margin-bottom: 15px;
    ">
    """,
    unsafe_allow_html=True
)
# ----------------------------------------------------------------------------
# LOAD DATA (with graceful failure)
# ----------------------------------------------------------------------------
try:
    latest = load_latest_metrics()
    daily = load_daily_summary()
    data_ok = True
except Exception as e:
    data_ok = False
    st.error(f"Could not reach the database. Is Postgres running? ({e})")
if data_ok and not latest.empty:
    # ---------------- Live asset cards ----------------
    st.markdown('<div class="section-label">LIVE · 5-MIN ROLLING METRICS</div>', unsafe_allow_html=True)
    cols = st.columns(len(latest))
    for i, (_, row) in enumerate(latest.iterrows()):
        with cols[i]:
            vol = row["volatility"] if pd.notna(row["volatility"]) else 0
            vol_display = f"{vol:.5f}" if pd.notna(row["volatility"]) else "—"
            state = "up" if vol == 0 else "down"       # up = calm/flat, down = moving
            vol_class = "vol-up" if state == "up" else "vol-down"
            st.markdown(f"""
            <div class="asset-card">
                <div class="asset-name"><span class="vol-dot {state}"></span>{row['asset']}</div>
                <div class="asset-price-row">
                    <div class="asset-price">${row['avg_price']:,.4f}</div>
                </div>
                <div class="asset-vol">VOLATILITY&nbsp;<b class="{vol_class}">{vol_display}</b></div>
            </div>
            """, unsafe_allow_html=True)
    # ---------------- Sparkline charts ----------------
    st.markdown('<div class="section-label">PRICE TREND · LAST WINDOWS</div>', unsafe_allow_html=True)
    chart_cols = st.columns(len(latest))
    for i, (_, row) in enumerate(latest.iterrows()):
        with chart_cols[i]:
            series = load_recent_series(row["asset"])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=series["window_start"],
                y=[series["avg_price"].min()] * len(series),
                mode="lines", line=dict(width=0),
                showlegend=False, hoverinfo="skip"
            ))
            fig.add_trace(go.Scatter(
                x=series["window_start"], y=series["avg_price"],
                mode="lines", line=dict(color=ACCENT_CYAN, width=2),
                fill="tonexty", fillcolor="rgba(79,209,232,0.08)",
                hovertemplate="%{y:$,.4f}<extra></extra>"
            ))
            fig.update_layout(
                height=110, margin=dict(l=0, r=0, t=4, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False, autorange=True),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    # ---------------- Daily OHLC summary ----------------
    st.markdown('<div class="section-label">HISTORICAL · DAILY OHLC (dbt)</div>', unsafe_allow_html=True)
    if not daily.empty:
        styled = daily.copy()
        styled.columns = ["Asset", "Date", "Open", "High", "Low", "Close", "Volume"]
        st.dataframe(
            styled.style.format({
                "Open": "${:,.4f}", "High": "${:,.4f}",
                "Low": "${:,.4f}", "Close": "${:,.4f}",
                "Volume": "{:,.2f}"
            }),
            use_container_width=True, height=360
        )
    else:
        st.info("No daily summary yet — the Airflow + dbt pipeline hasn't completed a run.")
elif data_ok and latest.empty:
    st.warning("Connected to Postgres, but `live_metrics` is empty. Make sure the producer and Spark job are running.")