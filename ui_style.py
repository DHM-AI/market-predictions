"""
AI Market Scanner — trading terminal theme.
Inspired by: dense dark dashboards, teal tickers, colored pill badges.
"""
import streamlit as st

# ── Color tokens ──────────────────────────────────────────────────────────────
BG       = "#141414"
CARD     = "#1e1e1e"
CARD2    = "#232323"
BORDER   = "#2a2a2a"
TEXT     = "#e8e8e8"
MUTED    = "#888888"
SUBTLE   = "#444444"
CYAN     = "#22d3ee"   # ticker symbols / links
GREEN    = "#22c55e"   # bullish / positive / LONG
RED      = "#ef4444"   # bearish / negative
ORANGE   = "#f97316"   # SHORT / warning
AMBER    = "#f59e0b"   # medium confidence
PURPLE   = "#a78bfa"   # RSI line / accent


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp {{ background: {BG} !important; }}

    section[data-testid="stSidebar"] {{
        background: #111 !important;
        border-right: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebarNav"] a {{ color: {MUTED} !important; font-size: 13px; }}
    [data-testid="stSidebarNav"] a:hover {{ color: {TEXT} !important; }}

    /* Live / status badges */
    .live-badge {{
        display: inline-flex; align-items: center; gap: 5px;
        background: rgba(34,211,238,0.1);
        border: 1px solid rgba(34,211,238,0.35);
        color: {CYAN};
        font-size: 10px; font-weight: 600;
        letter-spacing: 1px; text-transform: uppercase;
        padding: 2px 9px; border-radius: 4px;
        margin-left: 8px; vertical-align: middle;
    }}
    .live-dot {{
        width: 5px; height: 5px; border-radius: 50%;
        background: {CYAN};
        animation: blink 1.4s infinite;
        display: inline-block;
    }}
    @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}

    /* Section header */
    .sec-header {{
        font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: {MUTED};
        padding-bottom: 8px;
        border-bottom: 1px solid {BORDER};
        margin-bottom: 12px;
        display: flex; align-items: center; justify-content: space-between;
    }}
    .count-badge {{
        background: {CARD2}; border: 1px solid {BORDER};
        color: {MUTED}; font-size: 11px; font-weight: 600;
        padding: 1px 8px; border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* Metrics */
    div[data-testid="metric-container"] {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 6px !important;
        padding: 12px 14px !important;
    }}
    div[data-testid="metric-container"] label {{
        color: {MUTED} !important;
        font-size: 10px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 20px !important;
        font-weight: 600 !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {CYAN} !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 5px !important;
        font-size: 12px !important;
        letter-spacing: 0.5px;
    }}
    .stButton > button:hover {{ opacity: 0.88 !important; }}
    .stButton > button[kind="secondary"] {{
        background: {CARD} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 5px !important;
        color: {TEXT} !important;
        font-size: 13px !important;
    }}
    .stTextInput > div > div > input:focus {{ border-color: {CYAN} !important; }}
    .stTextInput > div > div > input::placeholder {{ color: {MUTED} !important; }}

    /* Dividers */
    hr {{ border-color: {BORDER} !important; margin: 14px 0 !important; }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 5px !important;
        color: {TEXT} !important;
        font-size: 12px !important;
    }}

    code {{ color: {CYAN} !important; }}
    .block-container {{ padding-top: 20px !important; }}
    </style>
    """, unsafe_allow_html=True)


def live_badge():
    return '<span class="live-badge"><span class="live-dot"></span>LIVE</span>'


def section_header(text: str, count: int | None = None):
    badge = f'<span class="count-badge">{count}</span>' if count is not None else ""
    st.markdown(f'<div class="sec-header"><span>{text}</span>{badge}</div>', unsafe_allow_html=True)


def page_title(title: str, subtitle: str = ""):
    sub = f'<p style="color:{MUTED};font-size:12px;margin-top:3px;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h2 style="color:{TEXT};font-weight:700;margin-bottom:0;font-size:20px;">'
        f'⚡ {title} {live_badge()}</h2>{sub}',
        unsafe_allow_html=True
    )


def score_chip(score: float) -> str:
    if score >= 70:
        return (f'<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
                f'color:{GREEN};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700;'
                f'padding:2px 8px;border-radius:4px;">{score:.0f}</span>')
    if score >= 50:
        return (f'<span style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);'
                f'color:{AMBER};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700;'
                f'padding:2px 8px;border-radius:4px;">{score:.0f}</span>')
    return (f'<span style="background:rgba(68,68,68,0.3);border:1px solid {BORDER};'
            f'color:{MUTED};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700;'
            f'padding:2px 8px;border-radius:4px;">{score:.0f}</span>')

score_pill = score_chip


def direction_html(d: str) -> str:
    if d == "bullish":
        return (f'<span style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.4);'
                f'color:{GREEN};font-size:10px;font-weight:700;letter-spacing:0.5px;'
                f'padding:2px 7px;border-radius:4px;">LONG</span>')
    if d == "bearish":
        return (f'<span style="background:rgba(249,115,22,0.15);border:1px solid rgba(249,115,22,0.4);'
                f'color:{ORANGE};font-size:10px;font-weight:700;letter-spacing:0.5px;'
                f'padding:2px 7px;border-radius:4px;">SHORT</span>')
    return (f'<span style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);'
            f'color:{AMBER};font-size:10px;font-weight:700;letter-spacing:0.5px;'
            f'padding:2px 7px;border-radius:4px;">WATCH</span>')

direction_badge = direction_html


def signal_tags(sigs: list) -> str:
    return "".join(
        f'<span style="display:inline-block;background:rgba(34,211,238,0.08);'
        f'border:1px solid rgba(34,211,238,0.25);color:{CYAN};'
        f'font-size:10px;padding:2px 8px;border-radius:4px;margin:2px;">{s}</span>'
        for s in sigs
    )


def agent_card(name: str, subtitle: str, value: str, status: str = "done") -> str:
    color = {"done": GREEN, "running": CYAN, "idle": SUBTLE, "warn": AMBER}.get(status, GREEN)
    pulse = "animation:blink 0.8s infinite;" if status == "running" else ""
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:6px;
                padding:12px 16px;margin-bottom:8px;
                display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="color:{TEXT};font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px;">
          <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
                       background:{color};{pulse}"></span>{name}
        </div>
        <div style="color:{MUTED};font-size:11px;margin-top:3px;margin-left:15px;">{subtitle}</div>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;color:{color};">{value}</div>
    </div>"""


def status_bar(text: str):
    st.markdown(
        f'<div style="border-top:1px solid {BORDER};padding:5px 0;'
        f'font-size:10px;color:{MUTED};letter-spacing:1px;margin-top:12px;">{text}</div>',
        unsafe_allow_html=True
    )
