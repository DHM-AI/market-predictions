"""
Dark trading terminal theme — injected into every Streamlit page.
Matches the aesthetic from the AI Market Scanner reference UI.
"""
import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    /* ── Base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background */
    .stApp { background-color: #0d0d0d; }
    section[data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #1e1e1e; }

    /* ── LIVE badge ── */
    .live-badge {
        display: inline-block;
        background: #00ff88;
        color: #000;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        padding: 2px 8px;
        border-radius: 3px;
        margin-left: 8px;
        vertical-align: middle;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.6; }
    }

    /* ── Agent cards ── */
    .agent-card {
        background: #161616;
        border: 1px solid #1e1e1e;
        border-left: 3px solid #00ff88;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .agent-card.running { border-left-color: #00ff88; }
    .agent-card.warning { border-left-color: #f59e0b; }
    .agent-card.error   { border-left-color: #ef4444; }
    .agent-card.idle    { border-left-color: #333; }

    .agent-name { font-size: 13px; font-weight: 600; color: #e8e8e8; }
    .agent-sub  { font-size: 11px; color: #555; margin-top: 2px; }
    .agent-count {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 700;
        color: #00ff88;
    }

    /* ── Ticker rows ── */
    .ticker-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid #1a1a1a;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
    }
    .ticker-sym  { color: #e8e8e8; font-weight: 600; width: 70px; }
    .ticker-price { color: #e8e8e8; }
    .ticker-up   { color: #00ff88; }
    .ticker-down { color: #ef4444; }

    /* ── Score pill ── */
    .score-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 700;
    }
    .score-high   { background: #052e16; color: #00ff88; border: 1px solid #00ff88; }
    .score-medium { background: #2d1f00; color: #f59e0b; border: 1px solid #f59e0b; }
    .score-low    { background: #1a1a1a; color: #555;    border: 1px solid #333; }

    /* ── Direction badge ── */
    .dir-bull { color: #00ff88; font-weight: 700; }
    .dir-bear { color: #ef4444; font-weight: 700; }
    .dir-mix  { color: #f59e0b; font-weight: 700; }

    /* ── Section header ── */
    .section-header {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #444;
        padding: 8px 0 4px;
        border-bottom: 1px solid #1e1e1e;
        margin-bottom: 12px;
    }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: #161616;
        border: 1px solid #1e1e1e;
        border-radius: 6px;
        padding: 14px !important;
    }
    div[data-testid="metric-container"] label {
        color: #555 !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e8e8e8 !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px !important;
    }

    /* ── Tables ── */
    .stDataFrame { border: 1px solid #1e1e1e !important; border-radius: 6px; }
    .stDataFrame thead tr th {
        background: #111 !important;
        color: #555 !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid #1e1e1e !important;
    }
    .stDataFrame tbody tr { background: #0d0d0d !important; }
    .stDataFrame tbody tr:hover { background: #161616 !important; }
    .stDataFrame tbody tr td { border-bottom: 1px solid #1a1a1a !important; color: #e8e8e8 !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: #00ff88 !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 4px !important;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover { background: #00cc6a !important; }
    .stButton > button[kind="secondary"] {
        background: #161616 !important;
        color: #e8e8e8 !important;
        border: 1px solid #333 !important;
    }

    /* ── Divider ── */
    hr { border-color: #1e1e1e !important; }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: #161616 !important;
        border: 1px solid #1e1e1e !important;
        border-radius: 4px !important;
        color: #e8e8e8 !important;
    }

    /* ── Plotly chart bg ── */
    .js-plotly-plot .plotly { background: #0d0d0d !important; }

    /* ── Info / warning / error boxes ── */
    .stAlert { border-radius: 4px !important; }
    div[data-baseweb="notification"] { background: #161616 !important; }

    /* ── Sidebar nav ── */
    [data-testid="stSidebarNav"] a { color: #555 !important; font-size: 13px; }
    [data-testid="stSidebarNav"] a:hover { color: #e8e8e8 !important; }
    [data-testid="stSidebarNav"] .active { color: #00ff88 !important; }

    /* ── Code / mono ── */
    code { font-family: 'JetBrains Mono', monospace !important; color: #00ff88 !important; }
    </style>
    """, unsafe_allow_html=True)


def live_badge():
    return '<span class="live-badge">LIVE</span>'


def agent_card(name: str, subtitle: str, value: str = "",
               status: str = "running") -> str:
    return f"""
    <div class="agent-card {status}">
        <div>
            <div class="agent-name">{name}</div>
            <div class="agent-sub">{subtitle}</div>
        </div>
        <div class="agent-count">{value}</div>
    </div>
    """


def score_pill(score: float) -> str:
    if score >= 70:
        cls = "score-high"
    elif score >= 50:
        cls = "score-medium"
    else:
        cls = "score-low"
    return f'<span class="score-pill {cls}">{score:.0f}</span>'


def direction_badge(direction: str) -> str:
    if direction == "bullish":
        return '<span class="dir-bull">▲ BULLISH</span>'
    if direction == "bearish":
        return '<span class="dir-bear">▼ BEARISH</span>'
    return '<span class="dir-mix">◆ MIXED</span>'


def section_header(text: str) -> None:
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def ticker_row(sym: str, price: float, change_pct: float) -> str:
    cls = "ticker-up" if change_pct >= 0 else "ticker-down"
    arrow = "▲" if change_pct >= 0 else "▼"
    return f"""
    <div class="ticker-row">
        <span class="ticker-sym">{sym}</span>
        <span class="ticker-price">${price:,.2f}</span>
        <span class="{cls}">{arrow} {abs(change_pct):.1f}%</span>
    </div>
    """
