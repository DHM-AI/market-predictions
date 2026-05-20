import streamlit as st
import os
from ui_style import inject_css, bbg_header, bbg_page_title, status_bar
from datetime import datetime

st.set_page_config(page_title="MKTPRED TERMINAL", page_icon="📡", layout="wide")
inject_css()

bbg_page_title("MKTPRED TERMINAL", "HOME GO")
st.markdown('<p style="color:#555;font-size:10px;letter-spacing:1px;margin-top:2px;margin-bottom:16px;">AI-POWERED MARKET PREDICTION SYSTEM  ·  STOCKS &amp; FUTURES  ·  XGBOOST + CLAUDE</p>', unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────────────
bbg_header("FUNCTION KEYS")
c1, c2, c3, c4 = st.columns(4)
c1.page_link("pages/1_Scanner.py",     label="F1  SCAN", use_container_width=True)
c2.page_link("pages/2_Ticker_Dive.py", label="F2  TICKER DV", use_container_width=True)
c3.page_link("pages/3_Track_Record.py",label="F3  RECORD", use_container_width=True)
c4.page_link("pages/4_Positions.py",   label="F4  POSITIONS", use_container_width=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# ── Agent pipeline status ──────────────────────────────────────────────────────
bbg_header("AGENT PIPELINE STATUS")

from model.predictor import model_available
import db

agents = [
    ("1 · SCAN",     "yfinance · 509 tickers · S&P 500 + futures",                True),
    ("2 · RESEARCH", "Reddit · RSS · Alpha Vantage · yfinance",                   True),
    ("3 · PREDICT",  "XGBoost" + (" ✓ MODEL LOADED" if model_available() else " ○ NO MODEL"),  True),
    ("4 · RISK",     "Kelly Criterion · $50,000 bankroll",                         True),
    ("5 · LEARN",    "Weekly post-mortem · auto-retrain · Supabase logging",       True),
]

for name, desc, active in agents:
    dot   = "●" if active else "○"
    color = "#F07D2A" if active else "#222"
    st.markdown(
        f'<div style="border-bottom:1px solid #0a0a0a;padding:8px 12px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'<span style="color:{color};font-size:10px;">{dot}</span>'
        f'<span style="color:#F07D2A;font-size:11px;font-weight:700;width:120px;">{name}</span>'
        f'<span style="color:#444;font-size:10px;">{desc}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown("<hr/>", unsafe_allow_html=True)

# ── System status ──────────────────────────────────────────────────────────────
bbg_header("SYSTEM CHECKLIST")

checks = [
    ("XGBOOST MODEL TRAINED",  model_available()),
    ("SUPABASE CONNECTED",     db.db_available()),
    ("ANTHROPIC API",          bool(os.environ.get("ANTHROPIC_API_KEY"))),
    ("ALPACA CONFIGURED",      bool(os.environ.get("ALPACA_API_KEY"))),
    ("ALPHA VANTAGE",          bool(os.environ.get("ALPHA_VANTAGE_KEY"))),
    ("GITHUB ACTIONS",         True),  # always true once deployed
]

cols = st.columns(3)
for i, (label, ok) in enumerate(checks):
    dot   = "● " if ok else "○ "
    color = "#F07D2A" if ok else "#333"
    status = "ACTIVE" if ok else "NOT SET"
    cols[i % 3].markdown(
        f'<div style="padding:10px;border:1px solid #111;margin:3px 0;">'
        f'<div style="color:{color};font-size:9px;letter-spacing:1px;">{dot}{label}</div>'
        f'<div style="color:#333;font-size:9px;margin-top:2px;">{status}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown("<hr/>", unsafe_allow_html=True)

# ── Getting started ────────────────────────────────────────────────────────────
bbg_header("QUICK START")
st.markdown("""
<div style="font-size:11px;color:#555;line-height:2;padding:10px 0;">
<span style="color:#F07D2A;">1)</span> Train model &nbsp;&nbsp;&nbsp;→ &nbsp;<span style="color:#ccc;">python -m model.trainer</span><br>
<span style="color:#F07D2A;">2)</span> Run scan &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ &nbsp;<span style="color:#ccc;">python agent.py --no-email --no-trade</span><br>
<span style="color:#F07D2A;">3)</span> Open dashboard → &nbsp;<span style="color:#ccc;">streamlit run app.py</span><br>
<span style="color:#F07D2A;">4)</span> Daily auto-scan → &nbsp;<span style="color:#ccc;">GitHub Actions · 08:00 ET weekdays</span><br>
<span style="color:#F07D2A;">5)</span> Paper trades &nbsp;&nbsp;→ &nbsp;<span style="color:#ccc;">Alpaca paper-api · score ≥ 70</span>
</div>
""", unsafe_allow_html=True)

status_bar(f"MKTPRED TERMINAL  ·  BUILD 2.0  ·  {datetime.now().strftime('%d %b %Y %H:%M')}  ·  PAPER TRADING MODE")
