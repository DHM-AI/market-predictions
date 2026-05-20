import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math

st.set_page_config(page_title="Market Scanner", page_icon="⚡", layout="wide")

# ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
BG    = "#03060d"
SURF  = "#07111f"
SURF2 = "#0c1d30"
GLOW  = "#00d4ff"       # cyan primary
GREEN = "#00ff88"       # bullish
RED   = "#ff2d78"       # bearish
AMBER = "#ffaa00"       # watch
TEXT  = "#c8e8ff"       # blue-white
TEXT2 = "#4a7a9b"       # muted
TEXT3 = "#1e3a50"       # very muted

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

*, body, html, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}

/* ── Deep space background with grid ── */
.stApp {{
    background: {BG} !important;
    background-image:
        linear-gradient(rgba(0,180,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,180,255,0.03) 1px, transparent 1px),
        radial-gradient(ellipse at 50% 0%, rgba(0,100,200,0.12) 0%, transparent 60%) !important;
    background-size: 44px 44px, 44px 44px, 100% 100% !important;
}}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background: {SURF} !important;
    border-right: 1px solid rgba(0,180,255,0.1) !important;
}}
[data-testid="stSidebarNav"] a {{
    color: {TEXT3} !important; font-size: 12px !important; font-weight: 500 !important;
    padding: 6px 12px !important; border-radius: 4px !important;
}}
[data-testid="stSidebarNav"] a:hover {{ color: {GLOW} !important; }}

/* ── Status bar ── */
.status-bar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 20px;
    background: rgba(7,17,31,0.9);
    border: 1px solid rgba(0,180,255,0.12);
    border-radius: 8px;
    margin-bottom: 18px;
    backdrop-filter: blur(10px);
}}
.status-item {{ display: flex; align-items: center; gap: 8px; }}
.status-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    animation: pulse-dot 2s infinite;
}}
@keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; box-shadow: 0 0 4px currentColor; }}
    50%       {{ opacity: 0.5; box-shadow: 0 0 10px currentColor; }}
}}
.status-label {{ font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }}
.status-val   {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; }}

/* ── Section label ── */
.section-label {{
    font-size: 9px; font-weight: 700; letter-spacing: 3px;
    text-transform: uppercase; color: {TEXT3};
    margin-bottom: 12px; display: flex; align-items: center; gap: 10px;
}}
.section-label::after {{
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(0,180,255,0.2), transparent);
}}

/* ── Pick card ── */
.pick-card {{
    position: relative;
    background: linear-gradient(135deg, rgba(12,29,48,0.95) 0%, rgba(7,17,31,0.95) 100%);
    border: 1px solid rgba(0,180,255,0.15);
    border-radius: 8px;
    padding: 16px;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;
    overflow: hidden;
}}
.pick-card::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--card-accent, {GLOW}), transparent);
    opacity: 0.6;
}}
/* Corner brackets */
.c {{ position: absolute; width: 10px; height: 10px; }}
.c-tl {{ top: 0; left: 0; border-top: 2px solid var(--card-accent, {GLOW}); border-left: 2px solid var(--card-accent, {GLOW}); border-radius: 2px 0 0 0; }}
.c-tr {{ top: 0; right: 0; border-top: 2px solid var(--card-accent, {GLOW}); border-right: 2px solid var(--card-accent, {GLOW}); border-radius: 0 2px 0 0; }}
.c-bl {{ bottom: 0; left: 0; border-bottom: 2px solid var(--card-accent, {GLOW}); border-left: 2px solid var(--card-accent, {GLOW}); border-radius: 0 0 0 2px; }}
.c-br {{ bottom: 0; right: 0; border-bottom: 2px solid var(--card-accent, {GLOW}); border-right: 2px solid var(--card-accent, {GLOW}); border-radius: 0 0 2px 0; }}

.pick-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
.pick-ticker {{ font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; line-height: 1; }}
.pick-dir {{
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    padding: 3px 8px; border-radius: 3px; margin-top: 5px;
}}
.pick-dur {{ font-size: 10px; color: {TEXT2}; margin-top: 3px; }}

/* Score ring is SVG, handled inline */

/* Signal bars */
.bar-wrap {{ margin-bottom: 14px; }}
.bar-row  {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
.bar-lbl  {{ font-size: 9px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: {TEXT2}; width: 76px; flex-shrink: 0; }}
.bar-track {{
    flex: 1; height: 5px; background: rgba(0,180,255,0.08);
    border-radius: 3px; overflow: hidden; position: relative;
}}
.bar-fill {{
    height: 5px; border-radius: 3px;
    position: relative;
    animation: bar-in 0.8s ease-out forwards;
}}
@keyframes bar-in {{
    from {{ width: 0 !important; opacity: 0; }}
    to   {{ opacity: 1; }}
}}
.bar-pct {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 600;
    min-width: 28px; text-align: right;
}}

/* Stats row */
.stats-row {{
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 8px; margin-top: 4px;
    border-top: 1px solid rgba(0,180,255,0.08);
    padding-top: 10px;
}}
.stat-cell {{ display: flex; flex-direction: column; gap: 2px; }}
.stat-lbl  {{ font-size: 9px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: {TEXT3}; }}
.stat-val  {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: {TEXT}; }}

/* Kelly row */
.kelly-row {{
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(0,180,255,0.05);
    border: 1px solid rgba(0,180,255,0.1);
    border-radius: 5px; padding: 7px 10px; margin-top: 10px;
}}
.kelly-lbl {{ font-size: 9px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: {TEXT2}; }}
.kelly-val {{ font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; }}

/* Chart container */
.chart-wrap {{
    background: {SURF};
    border: 1px solid rgba(0,180,255,0.12);
    border-radius: 8px; overflow: hidden;
    margin-top: 6px;
}}

/* No-data screen */
.waiting {{
    min-height: 60vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px; text-align: center;
}}
.waiting-ring {{
    width: 100px; height: 100px;
    border: 2px solid rgba(0,180,255,0.15);
    border-top: 2px solid {GLOW};
    border-radius: 50%;
    animation: spin 1.5s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.waiting-title {{ font-size: 18px; font-weight: 600; color: {TEXT}; }}
.waiting-sub   {{ font-size: 12px; color: {TEXT2}; line-height: 1.8; }}

/* Hide Streamlit top toolbar */
header[data-testid="stHeader"] {{ display: none !important; }}
.stAppHeader {{ display: none !important; }}
#stDecoration {{ display: none !important; }}

/* Streamlit overrides */
hr {{ border-color: rgba(0,180,255,0.08) !important; margin: 16px 0 !important; }}
.stButton > button {{
    background: rgba(0,180,255,0.1) !important;
    color: {GLOW} !important;
    border: 1px solid rgba(0,180,255,0.3) !important;
    border-radius: 6px !important;
    font-size: 12px !important; font-weight: 600 !important;
    letter-spacing: 0.5px;
}}
.stButton > button:hover {{ background: rgba(0,180,255,0.18) !important; }}
.stSelectbox label {{ color: {TEXT2} !important; font-size: 11px !important; }}
div[data-testid="stSelectbox"] > div {{ background: {SURF} !important; border-color: rgba(0,180,255,0.15) !important; }}
.block-container {{ padding-top: 18px !important; }}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def score_ring(score: float, accent: str, size: int = 62) -> str:
    """SVG circular progress ring for score."""
    r   = size // 2 - 6
    cx  = cy = size // 2
    circ = 2 * math.pi * r
    fill = circ * (score / 100)
    offset = circ - fill
    color = GREEN if score >= 70 else AMBER if score >= 50 else TEXT2
    font = max(12, size // 5)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="flex-shrink:0;">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(0,180,255,0.1)" stroke-width="4"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="4"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 {cx} {cy})"'
        f' style="filter:drop-shadow(0 0 4px {color});"/>'
        f'<text x="{cx}" y="{cy+font//3}" text-anchor="middle"'
        f' fill="{color}" font-size="{font}" font-weight="700" font-family="JetBrains Mono,monospace">'
        f'{score:.0f}</text>'
        f'</svg>'
    )

def signal_bar(label: str, pct: int, color: str) -> str:
    return (
        f'<div class="bar-row">'
        f'<span class="bar-lbl">{label}</span>'
        f'<div class="bar-track">'
        f'<div class="bar-fill" style="width:{pct}%;background:{color};'
        f'box-shadow:0 0 8px {color}66;"></div></div>'
        f'<span class="bar-pct" style="color:{color};">{pct}%</span>'
        f'</div>'
    )

def pick_card(row) -> str:
    ticker  = row.get("ticker", "")
    score   = float(row.get("score", 0))
    direct  = row.get("direction", "mixed")
    conf    = row.get("confidence", "—")
    dur     = row.get("duration", "—")
    rsi     = row.get("rsi", 0) or 0
    vol     = row.get("volume_ratio", 0) or 0
    kelly   = row.get("dollar_amount", 0) or 0
    bb_pct  = row.get("bb_pct", 0) or 0
    sent    = row.get("sentiment_score", 0) or 0
    xgb     = row.get("xgb_prob", 0) or 0

    if direct == "bullish":
        accent, dir_bg, dir_txt, dir_label = GREEN, "rgba(0,255,136,0.1)", GREEN, "↑ LONG"
    elif direct == "bearish":
        accent, dir_bg, dir_txt, dir_label = RED, "rgba(255,45,120,0.1)", RED, "↓ SHORT"
    else:
        accent, dir_bg, dir_txt, dir_label = AMBER, "rgba(255,170,0,0.1)", AMBER, "◆ WATCH"

    conf_c = {GREEN: "#00ff88", AMBER: "#ffaa00"}.get(
        {"High": GREEN, "Medium": AMBER}.get(conf, TEXT2), TEXT2)

    bb_v   = max(0, min(100, int((1 - bb_pct) * 100))) if bb_pct else int(score * 0.85)
    vol_v  = max(0, min(100, int((float(vol) / 4) * 100))) if vol else int(score * 0.65)
    sent_v = max(0, min(100, int((float(sent) + 1) * 50))) if sent else int(score * 0.58)
    xgb_v  = max(0, min(100, int(float(xgb) * 100))) if xgb else int(score * 0.75)

    ks = f"${kelly:,.0f}" if kelly else "—"
    rs = f"{float(rsi):.0f}" if rsi else "—"
    vs = f"{float(vol):.1f}×" if vol else "—"

    ring = score_ring(score, accent)

    bars = (signal_bar("BB SQUEEZE",  bb_v,   GLOW) +
            signal_bar("VOLUME",      vol_v,  GREEN) +
            signal_bar("SENTIMENT",   sent_v, AMBER) +
            signal_bar("XGBOOST",     xgb_v,  accent))

    return f"""
<div class="pick-card" style="--card-accent:{accent};">
  <span class="c c-tl" style="border-color:{accent};"></span>
  <span class="c c-tr" style="border-color:{accent};"></span>
  <span class="c c-bl" style="border-color:{accent};"></span>
  <span class="c c-br" style="border-color:{accent};"></span>

  <div class="pick-top">
    <div>
      <div class="pick-ticker" style="color:{accent};text-shadow:0 0 16px {accent}66;">{ticker}</div>
      <div class="pick-dir" style="background:{dir_bg};color:{dir_txt};border:1px solid {dir_txt}44;">
        {dir_label}
      </div>
      <div class="pick-dur">{dur} &nbsp;·&nbsp; <span style="color:{conf_c};">{conf}</span></div>
    </div>
    {ring}
  </div>

  <div class="bar-wrap">{bars}</div>

  <div class="stats-row">
    <div class="stat-cell">
      <span class="stat-lbl">RSI</span>
      <span class="stat-val">{rs}</span>
    </div>
    <div class="stat-cell">
      <span class="stat-lbl">Volume</span>
      <span class="stat-val">{vs}</span>
    </div>
    <div class="stat-cell">
      <span class="stat-lbl">Auto-trade</span>
      <span class="stat-val" style="color:{'#00ff88' if score >= 70 else '#4a7a9b'};">
        {'✓ YES' if score >= 70 else '○ NO'}
      </span>
    </div>
  </div>

  <div class="kelly-row">
    <span class="kelly-lbl">Kelly Position</span>
    <span class="kelly-val" style="color:{GREEN};text-shadow:0 0 10px {GREEN}55;">{ks}</span>
  </div>
</div>"""

# ─── DATA ─────────────────────────────────────────────────────────────────────
picks_df = None
last_scan = ""
try:
    from db import load_predictions_for_date, db_available
    if db_available():
        rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
        if rows:
            picks_df = pd.DataFrame(rows)
            if "created_at" in picks_df.columns:
                ts = pd.to_datetime(picks_df["created_at"].iloc[0])
                last_scan = ts.strftime("%H:%M")
except Exception:
    pass

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
n_auto  = int((picks_df["score"] >= 70).sum()) if picks_df is not None and not picks_df.empty and "score" in picks_df.columns else 0

# Alpaca status
alpaca_ok = False
alpaca_label = "NOT CONNECTED"
try:
    from execution.alpaca import is_configured, is_live_mode
    alpaca_ok = is_configured()
    alpaca_label = ("🔴 LIVE" if is_live_mode() else "PAPER") if alpaca_ok else "NOT CONNECTED"
except Exception:
    pass

# ─── STATUS BAR ───────────────────────────────────────────────────────────────
scan_info = f"Last scan {last_scan}" if last_scan else "Runs 8 AM ET weekdays"
st.markdown(f"""
<div class="status-bar">
  <div style="display:flex;align-items:center;gap:24px;">
    <div class="status-item">
      <div class="status-dot" style="background:{GREEN if n_picks else TEXT3};color:{GREEN if n_picks else TEXT3};"></div>
      <span class="status-label" style="color:{TEXT2};">Agent</span>
      <span class="status-val" style="color:{TEXT};">{scan_info}</span>
    </div>
    <div class="status-item">
      <div class="status-dot" style="background:{GREEN if alpaca_ok else AMBER};color:{GREEN if alpaca_ok else AMBER};"></div>
      <span class="status-label" style="color:{TEXT2};">Alpaca</span>
      <span class="status-val" style="color:{GREEN if alpaca_ok else AMBER};">{alpaca_label}</span>
    </div>
    <div class="status-item">
      <div class="status-dot" style="background:{GLOW};color:{GLOW};"></div>
      <span class="status-label" style="color:{TEXT2};">Auto-trade</span>
      <span class="status-val" style="color:{TEXT};">Score ≥ 70 &nbsp;·&nbsp; {n_auto} eligible today</span>
    </div>
  </div>
  <div class="status-item">
    <span class="status-val" style="color:{TEXT2};">{n_picks} setups &nbsp;·&nbsp; {datetime.today().strftime('%b %d %Y')}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    sorted_df = picks_df.sort_values("score", ascending=False)

    st.markdown(
        f'<div class="section-label">Today\'s Predictions &nbsp;·&nbsp; {n_picks} setups flagged</div>',
        unsafe_allow_html=True)

    # Card grid — 3 per row
    chunks = [sorted_df.iloc[i:i+3] for i in range(0, len(sorted_df), 3)]
    for chunk in chunks:
        cols = st.columns(3)
        for ci, (_, row) in enumerate(chunk.iterrows()):
            with cols[ci]:
                st.markdown(pick_card(row), unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Chart ──────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-label">Chart</div>',
        unsafe_allow_html=True)

    tickers = sorted_df["ticker"].tolist()
    sel = st.selectbox("", tickers, label_visibility="collapsed")

    if sel:
        try:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            from ta.momentum  import RSIIndicator

            df_c = get_ohlcv(sel, period="6mo")
            if not df_c.empty:
                _bb  = BB(df_c["Close"], window=20, window_dev=2)
                _rsi = RSIIndicator(df_c["Close"], window=14).rsi()

                fig = go.Figure()

                # BB bands
                try:
                    fig.add_trace(go.Scatter(
                        x=df_c.index, y=_bb.bollinger_hband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1),
                        showlegend=False, name="BB Upper"))
                    fig.add_trace(go.Scatter(
                        x=df_c.index, y=_bb.bollinger_lband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1),
                        fill="tonexty", fillcolor="rgba(0,212,255,0.04)",
                        showlegend=False, name="BB Lower"))
                except Exception:
                    pass

                # Candles
                fig.add_trace(go.Candlestick(
                    x=df_c.index,
                    open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"],   close=df_c["Close"],
                    name=sel,
                    increasing=dict(line=dict(color=GREEN, width=1.2),
                                    fillcolor="rgba(0,255,136,0.2)"),
                    decreasing=dict(line=dict(color=RED, width=1.2),
                                    fillcolor="rgba(255,45,120,0.2)")))

                row_data = sorted_df[sorted_df["ticker"] == sel].iloc[0]
                score    = float(row_data.get("score", 0))
                direct   = row_data.get("direction", "mixed")
                accent   = GREEN if direct == "bullish" else RED if direct == "bearish" else AMBER

                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    height=360,
                    paper_bgcolor=SURF, plot_bgcolor=SURF,
                    xaxis=dict(
                        gridcolor="rgba(0,180,255,0.06)",
                        tickfont=dict(color=TEXT2, size=10),
                        showgrid=True),
                    yaxis=dict(
                        gridcolor="rgba(0,180,255,0.06)",
                        tickfont=dict(color=TEXT2, size=10),
                        showgrid=True, side="right"),
                    margin=dict(l=0, r=56, t=28, b=0),
                    title=dict(
                        text=f"<b style='color:{accent}'>{sel}</b>"
                             f"<span style='color:{TEXT2};font-size:12px;'>"
                             f"  ·  Score {score:.0f}  ·  6-Month</span>",
                        font=dict(color=TEXT, size=13), x=0.01),
                )
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(
                f'<div style="color:{TEXT2};padding:20px;text-align:center;font-size:12px;">Chart unavailable: {e}</div>',
                unsafe_allow_html=True)

else:
    # Waiting state
    st.markdown(f"""
    <div class="waiting">
      <div class="waiting-ring"></div>
      <div class="waiting-title">Awaiting Market Scan</div>
      <div class="waiting-sub">
        The agent runs every weekday at <strong style="color:{GLOW};">8:00 AM ET</strong> via GitHub Actions.<br>
        It scans S&amp;P 500 + Futures, scores setups, and writes predictions here automatically.<br><br>
        <span style="color:{AMBER};">First run triggered — check back in ~15 minutes.</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
