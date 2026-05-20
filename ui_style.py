"""
AI Market Scanner UI — matches the dark green terminal from the reference screenshots.
Black background · #00ff88 green · Clean Inter font · Minimal monospace for numbers only.
"""
import streamlit as st
from datetime import datetime


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Base ─────────────────────────────────────────────── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background: #0d0d0d !important; }
    section[data-testid="stSidebar"] {
        background: #0a0a0a !important;
        border-right: 1px solid #1a1a1a !important;
    }

    /* ── LIVE badge ───────────────────────────────────────── */
    .live-badge {
        display: inline-flex; align-items: center; gap: 5px;
        background: rgba(0,255,136,0.1);
        border: 1px solid #00ff88;
        color: #00ff88;
        font-size: 10px; font-weight: 700;
        letter-spacing: 2px;
        padding: 2px 10px;
        border-radius: 3px;
        margin-left: 10px;
        vertical-align: middle;
    }
    .live-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: #00ff88;
        animation: blink 1.2s infinite;
        display: inline-block;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

    /* ── Agent / panel cards ──────────────────────────────── */
    .agent-card {
        background: #111;
        border: 1px solid #1a1a1a;
        border-left: 3px solid #00ff88;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .agent-card.idle    { border-left-color: #222; }
    .agent-card.warn    { border-left-color: #f59e0b; }
    .agent-card.done    { border-left-color: #00ff88; }
    .agent-title  { color: #e8e8e8; font-size: 13px; font-weight: 600; }
    .agent-sub    { color: #444; font-size: 11px; margin-top: 2px; }
    .agent-count  {
        font-family: 'JetBrains Mono', monospace;
        font-size: 24px; font-weight: 700; color: #00ff88;
    }

    /* ── Pipeline steps ───────────────────────────────────── */
    .pip-row {
        display: flex; align-items: center;
        padding: 9px 14px; border-bottom: 1px solid #111;
        gap: 12px; font-size: 12px;
    }
    .pip-dot-on  { width:9px;height:9px;border-radius:50%;background:#00ff88;box-shadow:0 0 6px #00ff88;flex-shrink:0; }
    .pip-dot-ok  { width:9px;height:9px;border-radius:50%;background:#00ff88;flex-shrink:0; }
    .pip-dot-off { width:9px;height:9px;border-radius:50%;background:#1a1a1a;border:1px solid #2a2a2a;flex-shrink:0; }
    .pip-label   { color:#e8e8e8;font-weight:500;flex:1; }
    .pip-sub     { color:#333;font-size:10px; }
    .pip-bar     { flex:1;height:3px;background:#1a1a1a;border-radius:2px;max-width:100px; }
    .pip-bar-fill { height:3px;background:#00ff88;border-radius:2px; }
    .pip-num-on  { font-family:'JetBrains Mono',monospace;color:#00ff88;font-weight:600;min-width:44px;text-align:right; }
    .pip-num-ok  { font-family:'JetBrains Mono',monospace;color:#00ff88;font-weight:600;min-width:44px;text-align:right; }
    .pip-num-off { font-family:'JetBrains Mono',monospace;color:#222;min-width:44px;text-align:right; }

    /* ── Qualified box ────────────────────────────────────── */
    .qual-box {
        background: #0a1f14;
        border: 1px solid #00ff88;
        border-radius: 6px;
        padding: 14px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
    }
    .qual-label { color: #00ff88; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; }
    .qual-count { font-family:'JetBrains Mono',monospace; font-size:30px; font-weight:700; color:#00ff88; }

    /* ── Ticker tape ──────────────────────────────────────── */
    .tape-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 12px; border-bottom: 1px solid #111;
        font-size: 12px; cursor: pointer;
    }
    .tape-row:hover { background: #111; }
    .tape-sym   { color: #00ff88; font-weight: 700; width: 60px; font-family: 'JetBrains Mono', monospace; }
    .tape-price { color: #888; font-family: 'JetBrains Mono', monospace; flex: 1; text-align: right; padding-right: 12px; }
    .tape-up    { color: #00ff88; font-family: 'JetBrains Mono', monospace; min-width: 54px; text-align: right; }
    .tape-dn    { color: #ff4444; font-family: 'JetBrains Mono', monospace; min-width: 54px; text-align: right; }

    /* ── Score chips ──────────────────────────────────────── */
    .chip-hi  { background:#0a1f14;color:#00ff88;border:1px solid #00ff88;padding:2px 8px;font-size:11px;font-weight:700;border-radius:3px;font-family:'JetBrains Mono',monospace; }
    .chip-med { background:#1a1500;color:#f59e0b;border:1px solid #f59e0b;padding:2px 8px;font-size:11px;font-weight:700;border-radius:3px;font-family:'JetBrains Mono',monospace; }
    .chip-lo  { background:#111;color:#333;border:1px solid #222;padding:2px 8px;font-size:11px;font-weight:700;border-radius:3px;font-family:'JetBrains Mono',monospace; }

    /* ── Direction ────────────────────────────────────────── */
    .dir-bull { color:#00ff88;font-weight:700; }
    .dir-bear { color:#ff4444;font-weight:700; }
    .dir-mix  { color:#f59e0b;font-weight:600; }

    /* ── Section headers ──────────────────────────────────── */
    .sec-header {
        font-size: 10px; font-weight: 600; letter-spacing: 2px;
        text-transform: uppercase; color: #333;
        padding: 6px 0 4px; border-bottom: 1px solid #1a1a1a;
        margin-bottom: 12px;
    }

    /* ── Metrics ──────────────────────────────────────────── */
    div[data-testid="metric-container"] {
        background: #111 !important;
        border: 1px solid #1a1a1a !important;
        border-top: 2px solid #00ff88 !important;
        border-radius: 6px !important;
        padding: 12px 14px !important;
    }
    div[data-testid="metric-container"] label {
        color: #333 !important; font-size: 10px !important;
        text-transform: uppercase; letter-spacing: 1px;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e8e8e8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 22px !important; font-weight: 600 !important;
    }

    /* ── Buttons ──────────────────────────────────────────── */
    .stButton > button {
        background: #00ff88 !important; color: #000 !important;
        font-weight: 700 !important; border: none !important;
        border-radius: 5px !important; font-size: 12px !important;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover { background: #00cc6a !important; }
    .stButton > button[kind="secondary"] {
        background: #111 !important; color: #e8e8e8 !important;
        border: 1px solid #2a2a2a !important;
    }

    /* ── Inputs ───────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background: #111 !important; border: 1px solid #1a1a1a !important;
        border-radius: 5px !important; color: #e8e8e8 !important;
        font-size: 13px !important;
    }
    .stTextInput > div > div > input:focus { border-color: #00ff88 !important; }

    /* ── Tables ───────────────────────────────────────────── */
    .stDataFrame { border: 1px solid #1a1a1a !important; border-radius: 6px; }
    .stDataFrame thead tr th {
        background: #111 !important; color: #333 !important;
        font-size: 10px !important; text-transform: uppercase; letter-spacing: 1px;
        border-bottom: 1px solid #1a1a1a !important;
    }
    .stDataFrame tbody tr td { color: #e8e8e8 !important; border-bottom: 1px solid #0d0d0d !important; }
    .stDataFrame tbody tr:hover td { background: #111 !important; }

    /* ── Dividers ─────────────────────────────────────────── */
    hr { border-color: #1a1a1a !important; }

    /* ── Expander ─────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: #111 !important; border: 1px solid #1a1a1a !important;
        border-radius: 5px !important; color: #e8e8e8 !important;
        font-size: 12px !important;
    }

    /* ── Nav sidebar ──────────────────────────────────────── */
    [data-testid="stSidebarNav"] a { color: #333 !important; font-size: 12px; }
    [data-testid="stSidebarNav"] a:hover { color: #00ff88 !important; }

    code { color: #00ff88 !important; }
    .block-container { padding-top: 24px !important; }
    </style>
    """, unsafe_allow_html=True)


def live_badge():
    return '<span class="live-badge"><span class="live-dot"></span>LIVE</span>'


def section_header(text: str):
    st.markdown(f'<div class="sec-header">{text}</div>', unsafe_allow_html=True)


def page_title(title: str, subtitle: str = ""):
    sub = f'<p style="color:#444;font-size:12px;margin-top:2px;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h2 style="color:#e8e8e8;font-weight:700;margin-bottom:0;">'
        f'{title}{live_badge()}</h2>{sub}',
        unsafe_allow_html=True
    )


def agent_card(name: str, subtitle: str, value: str, status: str = "done") -> str:
    dot_color = {"done": "#00ff88", "running": "#00ff88", "idle": "#222", "warn": "#f59e0b"}.get(status, "#00ff88")
    pulse = "animation:blink 0.8s infinite;" if status == "running" else ""
    return f"""
    <div class="agent-card {status}">
      <div>
        <div class="agent-title">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
            background:{dot_color};margin-right:8px;{pulse}"></span>{name}
        </div>
        <div class="agent-sub">{subtitle}</div>
      </div>
      <div class="agent-count">{value}</div>
    </div>"""


def score_chip(score: float) -> str:
    if score >= 70: return f'<span class="chip-hi">{score:.0f}</span>'
    if score >= 50: return f'<span class="chip-med">{score:.0f}</span>'
    return f'<span class="chip-lo">{score:.0f}</span>'


def direction_html(d: str) -> str:
    if d == "bullish": return '<span class="dir-bull">▲ BULL</span>'
    if d == "bearish": return '<span class="dir-bear">▼ BEAR</span>'
    return '<span class="dir-mix">◆ WTCH</span>'


def signal_tags(sigs: list) -> str:
    return "".join(
        f'<span style="display:inline-block;background:#0a1f14;border:1px solid #00ff88;'
        f'color:#00ff88;font-size:10px;padding:2px 8px;border-radius:3px;margin:2px;">{s}</span>'
        for s in sigs
    )


def status_bar(text: str):
    st.markdown(
        f'<div style="border-top:1px solid #1a1a1a;padding:5px 0;'
        f'font-size:10px;color:#333;letter-spacing:1px;margin-top:16px;">{text}</div>',
        unsafe_allow_html=True
    )
