"""
AI Market Scanner — clean modern dark theme.
Zinc backgrounds · Indigo accent · Inter + JetBrains Mono
"""
import streamlit as st

# ── Color tokens ──────────────────────────────────────────────────────────────
BG       = "#09090b"   # zinc-950
CARD     = "#18181b"   # zinc-900
BORDER   = "#27272a"   # zinc-800
TEXT     = "#fafafa"   # primary text
MUTED    = "#71717a"   # zinc-500
SUBTLE   = "#3f3f46"   # zinc-700
ACCENT   = "#6366f1"   # indigo-500
ACCENT_L = "#818cf8"   # indigo-400 (lighter)
GREEN    = "#22c55e"   # green-500
RED      = "#ef4444"   # red-500
AMBER    = "#f59e0b"   # amber-500


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp {{ background: {BG} !important; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {CARD} !important;
        border-right: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebarNav"] a {{
        color: {MUTED} !important;
        font-size: 13px;
        font-weight: 500;
    }}
    [data-testid="stSidebarNav"] a:hover {{ color: {TEXT} !important; }}

    /* Live badge */
    .live-badge {{
        display: inline-flex; align-items: center; gap: 5px;
        background: rgba(99,102,241,0.12);
        border: 1px solid rgba(99,102,241,0.4);
        color: {ACCENT_L};
        font-size: 10px; font-weight: 600;
        letter-spacing: 1.5px; text-transform: uppercase;
        padding: 2px 10px; border-radius: 20px;
        margin-left: 10px; vertical-align: middle;
    }}
    .live-dot {{
        width: 5px; height: 5px; border-radius: 50%;
        background: {ACCENT_L};
        animation: pulse 1.8s infinite;
        display: inline-block;
    }}
    @keyframes pulse {{
        0%,100% {{ opacity:1; transform:scale(1); }}
        50% {{ opacity:0.4; transform:scale(0.8); }}
    }}

    /* Cards */
    .card {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 10px;
    }}

    /* Metrics */
    div[data-testid="metric-container"] {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        padding: 14px 16px !important;
    }}
    div[data-testid="metric-container"] label {{
        color: {MUTED} !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 20px !important;
        font-weight: 600 !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {ACCENT} !important;
        color: #fff !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        letter-spacing: 0.3px;
        transition: background 0.15s;
    }}
    .stButton > button:hover {{ background: #4f46e5 !important; }}
    .stButton > button[kind="secondary"] {{
        background: {CARD} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: {BORDER} !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        color: {TEXT} !important;
        font-size: 14px !important;
    }}
    .stTextInput > div > div > input:focus {{ border-color: {ACCENT} !important; }}
    .stTextInput > div > div > input::placeholder {{ color: {MUTED} !important; }}

    /* Dividers */
    hr {{ border-color: {BORDER} !important; margin: 16px 0 !important; }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        color: {TEXT} !important;
        font-size: 13px !important;
    }}

    /* Section headers */
    .sec-header {{
        font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; color: {MUTED};
        padding-bottom: 8px;
        border-bottom: 1px solid {BORDER};
        margin-bottom: 14px;
    }}

    /* Score badges */
    .score-high {{
        display: inline-block;
        background: rgba(34,197,94,0.1);
        border: 1px solid rgba(34,197,94,0.3);
        color: {GREEN};
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; font-weight: 700;
        padding: 2px 8px; border-radius: 6px;
    }}
    .score-med {{
        display: inline-block;
        background: rgba(245,158,11,0.1);
        border: 1px solid rgba(245,158,11,0.3);
        color: {AMBER};
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; font-weight: 700;
        padding: 2px 8px; border-radius: 6px;
    }}
    .score-lo {{
        display: inline-block;
        background: rgba(113,113,122,0.1);
        border: 1px solid {SUBTLE};
        color: {MUTED};
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; font-weight: 700;
        padding: 2px 8px; border-radius: 6px;
    }}

    /* Direction pills */
    .dir-bull {{
        display: inline-flex; align-items: center; gap: 4px;
        background: rgba(34,197,94,0.08);
        border: 1px solid rgba(34,197,94,0.25);
        color: {GREEN}; font-size: 11px; font-weight: 600;
        padding: 2px 8px; border-radius: 20px;
    }}
    .dir-bear {{
        display: inline-flex; align-items: center; gap: 4px;
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.25);
        color: {RED}; font-size: 11px; font-weight: 600;
        padding: 2px 8px; border-radius: 20px;
    }}
    .dir-mix {{
        display: inline-flex; align-items: center; gap: 4px;
        background: rgba(245,158,11,0.08);
        border: 1px solid rgba(245,158,11,0.25);
        color: {AMBER}; font-size: 11px; font-weight: 600;
        padding: 2px 8px; border-radius: 20px;
    }}

    code {{ color: {ACCENT_L} !important; }}
    .block-container {{ padding-top: 24px !important; }}
    </style>
    """, unsafe_allow_html=True)


def live_badge():
    return '<span class="live-badge"><span class="live-dot"></span>LIVE</span>'


def section_header(text: str):
    st.markdown(f'<div class="sec-header">{text}</div>', unsafe_allow_html=True)


def page_title(title: str, subtitle: str = ""):
    sub = f'<p style="color:{MUTED};font-size:13px;margin-top:4px;font-weight:400;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<h2 style="color:{TEXT};font-weight:700;margin-bottom:0;font-size:24px;">'
        f'{title} {live_badge()}</h2>{sub}',
        unsafe_allow_html=True
    )


def score_chip(score: float) -> str:
    if score >= 70:
        return f'<span class="score-high">{score:.0f}</span>'
    if score >= 50:
        return f'<span class="score-med">{score:.0f}</span>'
    return f'<span class="score-lo">{score:.0f}</span>'

# Alias used in Ticker Dive
score_pill = score_chip


def direction_html(d: str) -> str:
    if d == "bullish":
        return '<span class="dir-bull">↑ Bull</span>'
    if d == "bearish":
        return '<span class="dir-bear">↓ Bear</span>'
    return '<span class="dir-mix">◆ Watch</span>'

# Alias used in Ticker Dive
direction_badge = direction_html


def signal_tags(sigs: list) -> str:
    return "".join(
        f'<span style="display:inline-block;background:rgba(99,102,241,0.08);'
        f'border:1px solid rgba(99,102,241,0.3);color:{ACCENT_L};'
        f'font-size:11px;padding:2px 9px;border-radius:20px;margin:2px;">{s}</span>'
        for s in sigs
    )


def agent_card(name: str, subtitle: str, value: str, status: str = "done") -> str:
    color = {
        "done":    GREEN,
        "running": ACCENT_L,
        "idle":    SUBTLE,
        "warn":    AMBER,
    }.get(status, GREEN)
    pulse = "animation:pulse 0.9s infinite;" if status == "running" else ""
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;
                padding:14px 18px;margin-bottom:8px;
                display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="color:{TEXT};font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px;">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                       background:{color};{pulse}"></span>{name}
        </div>
        <div style="color:{MUTED};font-size:11px;margin-top:3px;margin-left:16px;">{subtitle}</div>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:{color};">{value}</div>
    </div>"""


def status_bar(text: str):
    st.markdown(
        f'<div style="border-top:1px solid {BORDER};padding:6px 0;'
        f'font-size:10px;color:{MUTED};letter-spacing:1px;margin-top:16px;">{text}</div>',
        unsafe_allow_html=True
    )
