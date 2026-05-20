"""
Bloomberg Terminal–inspired UI system.
Black background · Orange accents · Dense monospace · Uppercase headers
"""
import streamlit as st
from datetime import datetime


def inject_css():
    now = datetime.now().strftime("%H:%M:%S  %d %b %Y")
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

    /* ══ RESET ══════════════════════════════════════════════════ */
    html, body, [class*="css"] {{
        font-family: 'IBM Plex Mono', 'Courier New', monospace !important;
        background-color: #000 !important;
    }}
    .stApp {{ background: #000000 !important; }}
    section[data-testid="stSidebar"] {{
        background: #080808 !important;
        border-right: 1px solid #1a1a1a !important;
    }}

    /* ══ TOP FUNCTION BAR ════════════════════════════════════════ */
    .bbg-topbar {{
        position: fixed;
        top: 0; left: 0; right: 0;
        z-index: 9999;
        background: #000;
        border-bottom: 1px solid #F07D2A;
        display: flex;
        align-items: center;
        padding: 0 16px;
        height: 32px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
    }}
    .bbg-logo {{
        color: #F07D2A;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 2px;
        margin-right: 24px;
        border: 1px solid #F07D2A;
        padding: 1px 6px;
    }}
    .bbg-fn {{
        color: #888;
        margin-right: 20px;
        font-size: 10px;
        letter-spacing: 0.5px;
    }}
    .bbg-fn span {{ color: #F07D2A; }}
    .bbg-time {{ margin-left: auto; color: #F07D2A; font-size: 11px; letter-spacing: 1px; }}
    .bbg-spacer {{ height: 40px; }}

    /* ══ PANEL HEADERS ═══════════════════════════════════════════ */
    .bbg-panel-header {{
        background: #F07D2A;
        color: #000;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 3px 10px;
        margin-bottom: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .bbg-panel {{
        border: 1px solid #1e1e1e;
        margin-bottom: 12px;
        background: #000;
    }}
    .bbg-panel-body {{ padding: 0; }}

    /* ══ PIPELINE STEPS ══════════════════════════════════════════ */
    .pip-row {{
        display: flex;
        align-items: center;
        padding: 7px 10px;
        border-bottom: 1px solid #0a0a0a;
        gap: 10px;
        font-size: 11px;
    }}
    .pip-dot-on  {{ width:8px;height:8px;border-radius:50%;background:#F07D2A;
                    box-shadow:0 0 5px #F07D2A;flex-shrink:0; }}
    .pip-dot-ok  {{ width:8px;height:8px;border-radius:50%;background:#00C805;
                    box-shadow:0 0 5px #00C805;flex-shrink:0; }}
    .pip-dot-off {{ width:8px;height:8px;border-radius:50%;background:#111;
                    border:1px solid #222;flex-shrink:0; }}
    .pip-label   {{ color:#e8e8e8;flex:1;font-size:11px;letter-spacing:0.3px; }}
    .pip-sub     {{ color:#333;font-size:10px; }}
    .pip-bar     {{ flex:1;height:3px;background:#111;max-width:90px; }}
    .pip-bar-fill {{ height:3px;background:#F07D2A; }}
    .pip-num-on  {{ color:#F07D2A;font-weight:700;min-width:40px;text-align:right; }}
    .pip-num-ok  {{ color:#00C805;font-weight:700;min-width:40px;text-align:right; }}
    .pip-num-off {{ color:#222;min-width:40px;text-align:right; }}

    /* ══ QUALIFIED BOX ═══════════════════════════════════════════ */
    .qual-box {{
        border-top: 2px solid #F07D2A;
        padding: 12px 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #060300;
    }}
    .qual-label {{ color:#F07D2A;font-size:10px;letter-spacing:2px;text-transform:uppercase; }}
    .qual-count {{ font-size:26px;font-weight:700;color:#F07D2A;letter-spacing:1px; }}
    .qual-box.empty {{ border-top-color:#1e1e1e; }}
    .qual-box.empty .qual-label {{ color:#222; }}
    .qual-box.empty .qual-count {{ color:#222; }}

    /* ══ TICKER TAPE ═════════════════════════════════════════════ */
    .tape-row {{
        display: flex;
        justify-content: space-between;
        padding: 5px 10px;
        border-bottom: 1px solid #0a0a0a;
        font-size: 11px;
        cursor: pointer;
    }}
    .tape-row:hover {{ background:#0a0500; }}
    .tape-sym   {{ color:#F07D2A;font-weight:700;width:56px; }}
    .tape-price {{ color:#ccc;text-align:right;flex:1; }}
    .tape-up    {{ color:#00C805;text-align:right;width:52px; }}
    .tape-dn    {{ color:#FF3333;text-align:right;width:52px; }}

    /* ══ RESULTS TABLE ═══════════════════════════════════════════ */
    .bbg-table {{ width:100%;border-collapse:collapse;font-size:11px; }}
    .bbg-table th {{
        background:#0a0a0a;
        color:#555;
        padding:6px 10px;
        text-align:left;
        font-size:9px;
        letter-spacing:1.5px;
        text-transform:uppercase;
        border-bottom:1px solid #1a1a1a;
        font-weight:500;
    }}
    .bbg-table td {{
        padding:7px 10px;
        border-bottom:1px solid #0a0a0a;
        color:#ccc;
    }}
    .bbg-table tr:hover td {{ background:#050300; }}

    /* ══ SCORE CHIPS ═════════════════════════════════════════════ */
    .chip-hi  {{ color:#F07D2A;font-weight:700;border:1px solid #F07D2A;
                 padding:1px 6px;font-size:10px; }}
    .chip-med {{ color:#F0B82A;font-weight:700;border:1px solid #F0B82A;
                 padding:1px 6px;font-size:10px; }}
    .chip-lo  {{ color:#333;border:1px solid #222;padding:1px 6px;font-size:10px; }}

    /* ══ DIRECTION ════════════════════════════════════════════════ */
    .dir-bull {{ color:#00C805;font-weight:700;font-size:11px; }}
    .dir-bear {{ color:#FF3333;font-weight:700;font-size:11px; }}
    .dir-mix  {{ color:#888;font-size:11px; }}

    /* ══ METRICS ═════════════════════════════════════════════════ */
    div[data-testid="metric-container"] {{
        background:#000 !important;
        border:1px solid #1a1a1a !important;
        border-top:2px solid #F07D2A !important;
        border-radius:0 !important;
        padding:10px 14px !important;
    }}
    div[data-testid="metric-container"] label {{
        color:#555 !important;
        font-size:9px !important;
        letter-spacing:1.5px !important;
        text-transform:uppercase !important;
        font-family:'IBM Plex Mono',monospace !important;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color:#F07D2A !important;
        font-size:22px !important;
        font-family:'IBM Plex Mono',monospace !important;
        font-weight:700 !important;
    }}

    /* ══ BUTTONS ═════════════════════════════════════════════════ */
    .stButton > button {{
        background:#F07D2A !important;
        color:#000 !important;
        font-weight:700 !important;
        border:none !important;
        border-radius:0 !important;
        font-family:'IBM Plex Mono',monospace !important;
        font-size:11px !important;
        letter-spacing:1px !important;
        text-transform:uppercase !important;
    }}
    .stButton > button:hover {{ background:#c96000 !important; }}
    .stButton > button[kind="secondary"] {{
        background:#000 !important;
        color:#F07D2A !important;
        border:1px solid #F07D2A !important;
    }}

    /* ══ INPUTS ══════════════════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {{
        background:#000 !important;
        border:1px solid #1a1a1a !important;
        border-radius:0 !important;
        color:#e8e8e8 !important;
        font-family:'IBM Plex Mono',monospace !important;
        font-size:12px !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color:#F07D2A !important;
        box-shadow: 0 0 0 1px #F07D2A !important;
    }}

    /* ══ DIVIDER ═════════════════════════════════════════════════ */
    hr {{ border-color:#111 !important; margin:10px 0 !important; }}

    /* ══ SIDEBAR NAV ═════════════════════════════════════════════ */
    [data-testid="stSidebarNav"] a {{ color:#555 !important; font-size:11px; letter-spacing:0.5px; }}
    [data-testid="stSidebarNav"] a:hover {{ color:#F07D2A !important; }}

    /* ══ EXPANDER ════════════════════════════════════════════════ */
    .streamlit-expanderHeader {{
        background:#0a0a0a !important;
        border:1px solid #1a1a1a !important;
        border-radius:0 !important;
        color:#e8e8e8 !important;
        font-size:11px !important;
        font-family:'IBM Plex Mono',monospace !important;
    }}

    /* ══ DATAFRAME ════════════════════════════════════════════════ */
    .stDataFrame {{ border:1px solid #1a1a1a !important; }}
    .stDataFrame thead tr th {{
        background:#0a0a0a !important; color:#555 !important;
        font-size:9px !important; text-transform:uppercase;
        letter-spacing:1px; border-bottom:1px solid #1a1a1a !important;
        font-family:'IBM Plex Mono',monospace !important;
    }}
    .stDataFrame tbody tr td {{
        font-family:'IBM Plex Mono',monospace !important;
        font-size:11px !important; color:#ccc !important;
        border-bottom:1px solid #080808 !important;
    }}
    .stDataFrame tbody tr:hover td {{ background:#050300 !important; }}

    /* ══ MAIN PADDING RESET ══════════════════════════════════════ */
    .block-container {{ padding-top: 52px !important; }}

    /* ══ INFO/WARN/ERROR ═════════════════════════════════════════ */
    .stAlert {{ border-radius:0 !important; font-family:'IBM Plex Mono',monospace !important; font-size:11px !important; }}

    code {{ color:#F07D2A !important; font-family:'IBM Plex Mono',monospace !important; }}

    /* Plotly bg */
    .js-plotly-plot .plotly {{ background:#000 !important; }}
    </style>

    <!-- Fixed top function bar -->
    <div class="bbg-topbar">
      <div class="bbg-logo">MKTPRED</div>
      <div class="bbg-fn"><span>F1</span> SCAN</div>
      <div class="bbg-fn"><span>F2</span> TICKER</div>
      <div class="bbg-fn"><span>F3</span> RECORD</div>
      <div class="bbg-fn"><span>F4</span> POSITIONS</div>
      <div class="bbg-fn"><span>F8</span> RUN&nbsp;SCAN</div>
      <div class="bbg-time">{now} ET</div>
    </div>
    """, unsafe_allow_html=True)


# ── Helper renderers ──────────────────────────────────────────────────────────

def bbg_header(title: str, subtitle: str = ""):
    """Orange Bloomberg-style panel header."""
    sub_html = f'<span style="color:#000;font-size:9px;opacity:0.7;letter-spacing:1px;">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f'<div class="bbg-panel-header">'
        f'<span>{title}</span>{sub_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def bbg_page_title(title: str, code: str = ""):
    """Page title in Bloomberg style."""
    code_html = f' <span style="color:#555;font-size:11px;font-weight:400;">&lt;{code}&gt;</span>' if code else ""
    st.markdown(
        f'<h2 style="color:#F07D2A;font-family:IBM Plex Mono,monospace;'
        f'font-weight:700;font-size:18px;letter-spacing:1px;margin-bottom:0;">'
        f'{title}{code_html}</h2>',
        unsafe_allow_html=True
    )


def score_chip(score: float) -> str:
    if score >= 70:
        return f'<span class="chip-hi">{score:.0f}</span>'
    if score >= 50:
        return f'<span class="chip-med">{score:.0f}</span>'
    return f'<span class="chip-lo">{score:.0f}</span>'


def direction_html(d: str) -> str:
    if d == "bullish":
        return '<span class="dir-bull">▲ BUY</span>'
    if d == "bearish":
        return '<span class="dir-bear">▼ SELL</span>'
    return '<span class="dir-mix">◆ WTCH</span>'


def signal_tags(sigs: list) -> str:
    if not sigs:
        return ""
    return "".join(
        f'<span style="display:inline-block;border:1px solid #F07D2A;color:#F07D2A;'
        f'font-size:9px;padding:1px 6px;margin:2px;letter-spacing:1px;">{s}</span>'
        for s in sigs
    )


def status_bar(text: str):
    """Bottom-style status line."""
    st.markdown(
        f'<div style="border-top:1px solid #1a1a1a;padding:4px 10px;'
        f'font-size:10px;color:#444;letter-spacing:1px;margin-top:16px;">'
        f'{text}</div>',
        unsafe_allow_html=True
    )
