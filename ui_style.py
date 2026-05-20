"""
AI Market Scanner — terminal-grade dark design.
#0a0a0a base · #00ff88 green accent · JetBrains Mono numbers.
"""
import streamlit as st

# ── Tokens ────────────────────────────────────────────────────────────────────
BG      = "#080808"
CARD    = "#0f0f0f"
CARD2   = "#141414"
BORDER  = "#1e1e1e"
BORDER2 = "#2a2a2a"
TEXT    = "#f0f0f0"
TEXT2   = "#888888"
TEXT3   = "#444444"
GREEN   = "#00ff88"    # primary accent — neon green
RED     = "#ff3b5c"
AMBER   = "#f59e0b"
BLUE    = "#3b82f6"
CYAN    = "#22d3ee"    # tickers

# Aliases for other pages
SURF    = CARD
SURF2   = CARD2
MUTED   = TEXT2
BULL    = GREEN
BEAR    = RED
WATCH   = AMBER
ACCENT  = GREEN
ACCENT_L = GREEN
PURPLE  = "#a78bfa"
BORDER_TOKEN = BORDER


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    *, html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp {{ background: {BG} !important; }}

    section[data-testid="stSidebar"] {{
        background: {CARD} !important;
        border-right: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebarNav"] a {{
        color: {TEXT3} !important; font-size: 13px !important;
        font-weight: 500 !important; border-radius: 5px !important;
    }}
    [data-testid="stSidebarNav"] a:hover {{ color: {GREEN} !important; }}

    div[data-testid="metric-container"] {{
        background: {CARD} !important; border: 1px solid {BORDER} !important;
        border-radius: 8px !important; padding: 12px 14px !important;
    }}
    div[data-testid="metric-container"] label {{
        color: {TEXT3} !important; font-size: 10px !important;
        font-weight: 600 !important; text-transform: uppercase; letter-spacing: 1px;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {TEXT} !important; font-family: 'JetBrains Mono', monospace !important;
        font-size: 22px !important; font-weight: 700 !important;
    }}

    .stButton > button {{
        background: {GREEN} !important; color: #000 !important;
        font-weight: 700 !important; border: none !important;
        border-radius: 6px !important; font-size: 13px !important;
        letter-spacing: 0.3px; transition: opacity 0.15s;
    }}
    .stButton > button:hover {{ opacity: 0.85 !important; }}
    .stButton > button[kind="secondary"] {{
        background: {CARD} !important; color: {TEXT2} !important;
        border: 1px solid {BORDER2} !important;
    }}

    .stTextInput > div > div > input {{
        background: {CARD} !important; border: 1px solid {BORDER2} !important;
        border-radius: 6px !important; color: {TEXT} !important; font-size: 14px !important;
    }}
    .stTextInput > div > div > input:focus {{ border-color: {GREEN} !important; }}
    .stTextInput > div > div > input::placeholder {{ color: {TEXT3} !important; }}

    .stSelectbox label {{ color: {TEXT2} !important; font-size: 12px !important; }}

    hr {{ border: none !important; border-top: 1px solid {BORDER} !important; margin: 14px 0 !important; }}

    .streamlit-expanderHeader {{
        background: {CARD} !important; border: 1px solid {BORDER} !important;
        border-radius: 6px !important; color: {TEXT} !important; font-size: 12px !important;
    }}

    code {{ color: {GREEN} !important; }}
    .block-container {{ padding-top: 18px !important; padding-bottom: 40px !important; }}
    .stSpinner > div {{ border-top-color: {GREEN} !important; }}

    @keyframes glow {{
        0%,100% {{ box-shadow: 0 0 4px {GREEN}88; }}
        50%      {{ box-shadow: 0 0 10px {GREEN}cc; }}
    }}
    @keyframes blink {{
        0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def live_badge():
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.3);'
        f'color:{GREEN};font-size:9px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;padding:2px 9px;border-radius:3px;margin-left:10px;vertical-align:middle;">'
        f'<span style="width:5px;height:5px;border-radius:50%;background:{GREEN};'
        f'animation:blink 1.4s infinite;display:inline-block;"></span>LIVE</span>'
    )


def section_header(text: str, count=None):
    badge = (f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
             f'color:{TEXT3};background:{CARD2};border:1px solid {BORDER};'
             f'padding:1px 8px;border-radius:20px;margin-left:8px;">{count}</span>'
             if count is not None else "")
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:{TEXT3};margin-bottom:12px;'
        f'display:flex;align-items:center;">{text}{badge}</div>',
        unsafe_allow_html=True
    )


def page_title(title: str, subtitle: str = ""):
    sub = f'<p style="color:{TEXT2};font-size:12px;margin-top:3px;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h2 style="color:{TEXT};font-weight:700;font-size:20px;margin-bottom:0;">'
        f'{title} {live_badge()}</h2>{sub}', unsafe_allow_html=True
    )


def score_chip(score: float) -> str:
    if score >= 70:
        c = GREEN
    elif score >= 50:
        c = AMBER
    else:
        c = TEXT3
    w = int(score)
    return (
        f'<div style="display:flex;align-items:center;gap:7px;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-weight:700;'
        f'font-size:14px;color:{c};min-width:24px;">{score:.0f}</span>'
        f'<div style="flex:1;max-width:56px;height:3px;background:{BORDER2};border-radius:2px;">'
        f'<div style="width:{w}%;height:3px;background:{c};border-radius:2px;"></div>'
        f'</div></div>'
    )

score_pill = score_chip


def direction_html(d: str) -> str:
    if d == "bullish":
        return (f'<span style="background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.25);'
                f'color:{GREEN};font-size:10px;font-weight:700;letter-spacing:1px;'
                f'padding:3px 8px;border-radius:3px;">LONG</span>')
    if d == "bearish":
        return (f'<span style="background:rgba(255,59,92,0.1);border:1px solid rgba(255,59,92,0.25);'
                f'color:{RED};font-size:10px;font-weight:700;letter-spacing:1px;'
                f'padding:3px 8px;border-radius:3px;">SHORT</span>')
    return (f'<span style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.25);'
            f'color:{AMBER};font-size:10px;font-weight:700;letter-spacing:1px;'
            f'padding:3px 8px;border-radius:3px;">WATCH</span>')

direction_badge = direction_html


def signal_tags(sigs: list) -> str:
    return " ".join(
        f'<span style="display:inline-block;background:{CARD2};border:1px solid {BORDER2};'
        f'color:{TEXT2};font-size:10px;padding:2px 8px;border-radius:3px;margin:2px;">{s}</span>'
        for s in sigs
    )


def conf_bar(label: str, pct: float, color: str = GREEN) -> str:
    """Horizontal confidence bar — used in detail views."""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
        f'<span style="font-size:11px;color:{TEXT2};width:110px;flex-shrink:0;">{label}</span>'
        f'<div style="flex:1;height:6px;background:{BORDER2};border-radius:3px;">'
        f'<div style="width:{int(pct)}%;height:6px;background:{color};border-radius:3px;'
        f'box-shadow:0 0 6px {color}55;"></div></div>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
        f'color:{color};font-weight:600;min-width:32px;text-align:right;">{pct:.0f}%</span>'
        f'</div>'
    )


def agent_card(name: str, subtitle: str, value: str, status: str = "done") -> str:
    color = {"done": GREEN, "running": GREEN, "idle": TEXT3, "warn": AMBER}.get(status, GREEN)
    pulse = "animation:blink 0.8s infinite;" if status == "running" else ""
    return (
        f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:8px;'
        f'padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">'
        f'<div>'
        f'<div style="color:{TEXT};font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{color};'
        f'display:inline-block;{pulse}"></span>{name}</div>'
        f'<div style="color:{TEXT2};font-size:11px;margin-top:3px;margin-left:15px;">{subtitle}</div>'
        f'</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:22px;font-weight:700;color:{color};">{value}</div>'
        f'</div>'
    )


def status_bar(text: str):
    st.markdown(
        f'<div style="border-top:1px solid {BORDER};padding:5px 0;'
        f'font-size:10px;color:{TEXT3};letter-spacing:1px;margin-top:12px;">{text}</div>',
        unsafe_allow_html=True
    )
