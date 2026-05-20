"""
AI Market Scanner — premium dark design system.
Near-black surfaces · tight typography scale · purposeful color use.
"""
import streamlit as st

# ── Design tokens ─────────────────────────────────────────────────────────────
BG       = "#08080c"                       # near-black base
SURF     = "#101014"                       # card surface
SURF2    = "#16161c"                       # elevated surface
BORDER   = "rgba(255,255,255,0.07)"        # hairline border
BORDER2  = "rgba(255,255,255,0.12)"        # slightly stronger
TEXT     = "#f1f1f3"                       # primary text
TEXT2    = "#9898a8"                       # secondary / labels
TEXT3    = "#52525e"                       # muted / disabled
BULL     = "#10b981"                       # emerald — long / bullish
BEAR     = "#f43f5e"                       # rose    — short / bearish
WATCH    = "#f59e0b"                       # amber   — watch / medium
BLUE     = "#3b82f6"                       # blue    — button / accent
CYAN     = "#22d3ee"                       # cyan    — ticker symbols
PURPLE   = "#a78bfa"                       # purple  — RSI

# aliases used by Ticker Dive and Track Record pages
GREEN  = BULL
RED    = BEAR
AMBER  = WATCH
ACCENT = BLUE
ACCENT_L = "#60a5fa"
MUTED  = TEXT2
CARD   = SURF
BORDER_TOKEN = BORDER


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    *, html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        box-sizing: border-box;
    }}

    .stApp {{ background: {BG} !important; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {SURF} !important;
        border-right: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebarNav"] li {{
        padding: 2px 0;
    }}
    [data-testid="stSidebarNav"] a {{
        color: {TEXT3} !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
        transition: all 0.15s !important;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        color: {TEXT} !important;
        background: {SURF2} !important;
    }}

    /* Streamlit metrics (we barely use, but override anyway) */
    div[data-testid="metric-container"] {{
        background: {SURF} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
    }}
    div[data-testid="metric-container"] label {{
        color: {TEXT3} !important;
        font-size: 10px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 22px !important;
        font-weight: 700 !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {BLUE} !important;
        color: #fff !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        padding: 8px 20px !important;
        letter-spacing: 0.2px;
        transition: filter 0.15s;
    }}
    .stButton > button:hover {{ filter: brightness(1.12) !important; }}
    .stButton > button[kind="secondary"] {{
        background: {SURF} !important;
        color: {TEXT2} !important;
        border: 1px solid {BORDER2} !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        color: {TEXT} !important;
        border-color: {BORDER2} !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {{
        background: {SURF} !important;
        border: 1px solid {BORDER2} !important;
        border-radius: 8px !important;
        color: {TEXT} !important;
        font-size: 14px !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {BLUE} !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }}
    .stTextInput > div > div > input::placeholder {{ color: {TEXT3} !important; }}

    /* Selectbox */
    .stSelectbox label {{ color: {TEXT2} !important; font-size: 12px !important; }}

    /* Dividers */
    hr {{ border: none !important; border-top: 1px solid {BORDER} !important; margin: 16px 0 !important; }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {SURF} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        color: {TEXT} !important;
        font-size: 13px !important;
    }}

    /* Plotly chart bg fix */
    .js-plotly-plot {{ border-radius: 10px; overflow: hidden; }}

    /* Misc */
    code {{ color: {CYAN} !important; }}
    .block-container {{ padding-top: 20px !important; padding-bottom: 40px !important; }}
    .stSpinner > div {{ border-top-color: {BLUE} !important; }}
    </style>
    """, unsafe_allow_html=True)


# ── Component helpers ─────────────────────────────────────────────────────────

def live_badge():
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
        f'color:{BULL};font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;padding:2px 8px;border-radius:20px;'
        f'margin-left:10px;vertical-align:middle;">'
        f'<span style="width:5px;height:5px;border-radius:50%;background:{BULL};'
        f'animation:livepulse 1.6s infinite;display:inline-block;"></span>LIVE'
        f'</span>'
        f'<style>@keyframes livepulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}</style>'
    )


def section_header(text: str, count: int | None = None):
    badge = ""
    if count is not None:
        badge = (f'<span style="background:{SURF2};border:1px solid {BORDER2};'
                 f'color:{TEXT3};font-size:11px;font-weight:600;font-family:JetBrains Mono,monospace;'
                 f'padding:1px 9px;border-radius:20px;margin-left:8px;">{count}</span>')
    st.markdown(
        f'<div style="display:flex;align-items:center;margin-bottom:14px;">'
        f'<span style="font-size:11px;font-weight:600;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">{text}</span>{badge}</div>',
        unsafe_allow_html=True
    )


def page_title(title: str, subtitle: str = ""):
    sub = f'<p style="color:{TEXT2};font-size:13px;margin-top:4px;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h2 style="color:{TEXT};font-weight:700;font-size:22px;margin-bottom:0;">'
        f'{title} {live_badge()}</h2>{sub}',
        unsafe_allow_html=True
    )


def score_chip(score: float) -> str:
    """Score as a number + mini progress bar in one cell."""
    if score >= 70:
        color, bg = BULL, "rgba(16,185,129,0.12)"
    elif score >= 50:
        color, bg = WATCH, "rgba(245,158,11,0.12)"
    else:
        color, bg = TEXT3, "rgba(255,255,255,0.04)"
    bar_w = int(score)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:14px;'
        f'font-weight:700;color:{color};min-width:26px;">{score:.0f}</span>'
        f'<div style="width:52px;height:4px;background:rgba(255,255,255,0.07);border-radius:2px;flex-shrink:0;">'
        f'<div style="width:{bar_w}%;height:4px;background:{color};border-radius:2px;'
        f'box-shadow:0 0 6px {color}66;"></div></div>'
        f'</div>'
    )

score_pill = score_chip


def direction_html(d: str) -> str:
    if d == "bullish":
        return (f'<span style="display:inline-flex;align-items:center;gap:4px;'
                f'background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.25);'
                f'color:{BULL};font-size:11px;font-weight:700;letter-spacing:0.5px;'
                f'padding:3px 9px;border-radius:5px;">↑ LONG</span>')
    if d == "bearish":
        return (f'<span style="display:inline-flex;align-items:center;gap:4px;'
                f'background:rgba(244,63,94,0.12);border:1px solid rgba(244,63,94,0.25);'
                f'color:{BEAR};font-size:11px;font-weight:700;letter-spacing:0.5px;'
                f'padding:3px 9px;border-radius:5px;">↓ SHORT</span>')
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);'
            f'color:{WATCH};font-size:11px;font-weight:700;letter-spacing:0.5px;'
            f'padding:3px 9px;border-radius:5px;">◆ WATCH</span>')

direction_badge = direction_html


def signal_tags(sigs: list) -> str:
    return " ".join(
        f'<span style="display:inline-block;background:{SURF2};'
        f'border:1px solid {BORDER2};color:{TEXT2};'
        f'font-size:11px;padding:3px 10px;border-radius:5px;margin:2px;">{s}</span>'
        for s in sigs
    )


def agent_card(name: str, subtitle: str, value: str, status: str = "done") -> str:
    color = {
        "done":    BULL,
        "running": BLUE,
        "idle":    TEXT3,
        "warn":    WATCH,
    }.get(status, BULL)
    pulse = "animation:livepulse 0.9s infinite;" if status == "running" else ""
    return (
        f'<div style="background:{SURF};border:1px solid {BORDER};border-radius:10px;'
        f'padding:14px 16px;margin-bottom:8px;'
        f'display:flex;justify-content:space-between;align-items:center;">'
        f'<div>'
        f'<div style="color:{TEXT};font-size:13px;font-weight:600;'
        f'display:flex;align-items:center;gap:8px;">'
        f'<span style="width:7px;height:7px;border-radius:50%;'
        f'background:{color};display:inline-block;{pulse}"></span>{name}</div>'
        f'<div style="color:{TEXT2};font-size:11px;margin-top:3px;margin-left:15px;">{subtitle}</div>'
        f'</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;'
        f'font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


def status_bar(text: str):
    st.markdown(
        f'<div style="border-top:1px solid {BORDER};padding:6px 0;'
        f'font-size:10px;color:{TEXT3};letter-spacing:1px;margin-top:12px;">{text}</div>',
        unsafe_allow_html=True
    )
