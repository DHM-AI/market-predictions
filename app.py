import streamlit as st
from ui_style import inject_css, live_badge, agent_card, section_header
from model.predictor import model_available
import db

st.set_page_config(
    page_title="AI Market Scanner",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<h2 style="color:#e8e8e8;font-weight:700;letter-spacing:-0.5px;">'
    f'AI Market Scanner{live_badge()}</h2>'
    f'<p style="color:#444;font-size:13px;margin-top:-8px;">Prediction Markets · Stocks & Futures · Powered by XGBoost + Claude</p>',
    unsafe_allow_html=True
)

st.divider()

# ── Pipeline status cards ──────────────────────────────────────────────────────
section_header("AGENT PIPELINE")

c1, c2 = st.columns(2)
with c1:
    model_status = "running" if model_available() else "warning"
    model_label  = "XGBoost Model ✓" if model_available() else "No model — train first"
    st.markdown(agent_card("Scan + Predict Agent", model_label,
                           "Active" if model_available() else "⚠", model_status),
                unsafe_allow_html=True)
    st.markdown(agent_card("Research Agent",
                           "Reddit · RSS · Alpha Vantage · yfinance",
                           "5 sources", "running"),
                unsafe_allow_html=True)

with c2:
    db_status = "running" if db.db_available() else "warning"
    db_label  = "Supabase connected" if db.db_available() else "No DB — add credentials"
    st.markdown(agent_card("Risk Agent", f"Kelly Criterion · $50k bankroll",
                           "Active", "running"), unsafe_allow_html=True)
    st.markdown(agent_card("Learning Agent", "Weekly post-mortem · Auto-retrain",
                           "Sunday", "idle"), unsafe_allow_html=True)

st.divider()

# ── Quick nav ──────────────────────────────────────────────────────────────────
section_header("NAVIGATION")
col1, col2, col3, col4 = st.columns(4)
col1.page_link("pages/1_Scanner.py",    label="🔍  Scanner",         use_container_width=True)
col2.page_link("pages/2_Ticker_Dive.py", label="📊  Ticker Deep Dive", use_container_width=True)
col3.page_link("pages/3_Track_Record.py", label="📋  Track Record",    use_container_width=True)
col4.page_link("pages/4_Positions.py",  label="💼  Positions",        use_container_width=True)

st.divider()

# ── Setup checklist ────────────────────────────────────────────────────────────
section_header("SYSTEM STATUS")
checks = [
    ("XGBoost model trained",     model_available()),
    ("Supabase connected",        db.db_available()),
    ("Anthropic API configured",  bool(__import__('os').environ.get('ANTHROPIC_API_KEY'))),
    ("Alpaca configured",         bool(__import__('os').environ.get('ALPACA_API_KEY'))),
    ("Alpha Vantage configured",  bool(__import__('os').environ.get('ALPHA_VANTAGE_KEY'))),
]
for label, ok in checks:
    icon  = "🟢" if ok else "🔴"
    color = "#00ff88" if ok else "#ef4444"
    st.markdown(
        f'<div style="padding:4px 0;font-size:13px;">'
        f'{icon} <span style="color:{color};">{label}</span></div>',
        unsafe_allow_html=True
    )
