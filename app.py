import streamlit as st
import os
from ui_style import inject_css, page_title, section_header, agent_card, status_bar
from datetime import datetime

st.set_page_config(page_title="AI Market Scanner", page_icon="📡", layout="wide")
inject_css()

page_title("AI Market Scanner", "Stocks & Futures · 5-Agent Pipeline · 5-10% Move Detection")

# ── Navigation ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.page_link("pages/1_Scanner.py",      label="🔍  Scanner",        use_container_width=True)
c2.page_link("pages/2_Ticker_Dive.py",  label="📊  Ticker Deep Dive", use_container_width=True)
c3.page_link("pages/3_Track_Record.py", label="📋  Track Record",    use_container_width=True)
c4.page_link("pages/4_Positions.py",    label="💼  Positions",       use_container_width=True)

st.divider()

# ── Agent pipeline ─────────────────────────────────────────────────────────────
section_header("AGENT PIPELINE")

from model.predictor import model_available
import db

col1, col2 = st.columns(2)
with col1:
    st.markdown(agent_card("Scan Agent",
        "yfinance · 509 tickers · S&P 500 + Futures", "Active"), unsafe_allow_html=True)
    st.markdown(agent_card("Research Agent",
        "Reddit · RSS · Alpha Vantage · yfinance", "5 sources"), unsafe_allow_html=True)
with col2:
    model_label = "XGBoost ✓ loaded" if model_available() else "Rule-based fallback"
    st.markdown(agent_card("Predict Agent", model_label,
        "Active", "done" if model_available() else "warn"), unsafe_allow_html=True)
    st.markdown(agent_card("Risk Agent",
        "Kelly Criterion · $50,000 bankroll", "Active"), unsafe_allow_html=True)

st.markdown(agent_card("Learning Agent",
    "Weekly post-mortem · auto-retrain · Supabase logging",
    "Sunday", "idle"), unsafe_allow_html=True)

st.divider()

# ── System status ──────────────────────────────────────────────────────────────
section_header("SYSTEM STATUS")

checks = [
    ("XGBoost Model",    model_available(),                        "Trained & loaded"),
    ("Supabase",         db.db_available(),                        "Connected"),
    ("Anthropic API",    bool(os.environ.get("ANTHROPIC_API_KEY")), "Configured"),
    ("Alpaca",           bool(os.environ.get("ALPACA_API_KEY")),   "Paper mode"),
    ("Alpha Vantage",    bool(os.environ.get("ALPHA_VANTAGE_KEY")), "Configured"),
    ("GitHub Actions",   True,                                     "Daily 8 AM ET"),
]
cols = st.columns(3)
for i, (label, ok, detail) in enumerate(checks):
    dot   = "●" if ok else "○"
    color = "#00ff88" if ok else "#333"
    cols[i % 3].markdown(
        f'<div style="padding:10px;border:1px solid #1a1a1a;border-radius:6px;margin:3px 0;">'
        f'<div style="color:{color};font-size:12px;font-weight:600;">{dot} {label}</div>'
        f'<div style="color:#333;font-size:11px;margin-top:2px;">{detail if ok else "Not configured"}</div>'
        f'</div>', unsafe_allow_html=True
    )

status_bar(f"AI MARKET SCANNER  ·  v2.0  ·  {datetime.now().strftime('%d %b %Y %H:%M')}  ·  PAPER TRADING MODE")
