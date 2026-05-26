import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math
import html as _html

st.set_page_config(page_title="Illuminati", page_icon="🔺", layout="wide",
                   initial_sidebar_state="collapsed")


# ── Company name lookup — module-level so @st.cache_data works properly ────────
# Defined here (not inside fragments) so Streamlit can cache across reruns.
@st.cache_data(ttl=86400, show_spinner=False)
def _get_company_names(tickers: tuple) -> dict:
    """Fetch company short names from yfinance — cached 24 hours."""
    names = {}
    try:
        import yfinance as yf
        for t in tickers:
            try:
                names[t] = yf.Ticker(t).info.get("shortName") or ""
            except Exception:
                names[t] = ""
    except Exception:
        pass
    return names

BG    = "#03060d"
SURF  = "#07111f"
SURF2 = "#0c1d30"
GLOW  = "#00d4ff"
GREEN = "#00ff88"
RED   = "#ff2d78"
AMBER = "#ffaa00"
TEXT  = "#e8f4ff"   # primary — brighter white-blue
TEXT2 = "#8ab8d4"   # secondary — readable cyan-grey
TEXT3 = "#5a8a9f"   # labels / tertiary — was nearly invisible, now legible

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
*, body, html, [class*="css"] {{ font-family:'Inter',sans-serif !important; -webkit-font-smoothing:antialiased; }}
.stApp {{
    background:{BG} !important;
    background-image:
        linear-gradient(rgba(0,180,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,180,255,0.025) 1px, transparent 1px),
        radial-gradient(ellipse at 50% 0%, rgba(0,80,180,0.10) 0%, transparent 60%) !important;
    background-size:48px 48px, 48px 48px, 100% 100% !important;
}}
header[data-testid="stHeader"] {{ display:none !important; }}
.stAppHeader {{ display:none !important; }}
#stDecoration {{ display:none !important; }}
footer {{ display:none !important; }}
footer * {{ display:none !important; }}
[data-testid="stBottom"] {{ display:none !important; }}
[data-testid="stBottom"] * {{ display:none !important; }}
.viewerBadge_container__r5tak {{ display:none !important; }}
.viewerBadge_link__qRIco {{ display:none !important; }}
#MainMenu {{ display:none !important; }}
.st-emotion-cache-h4xjwg {{ display:none !important; }}
.st-emotion-cache-1dp5vir {{ display:none !important; }}
/* Nuclear option — hide any fixed bottom bar */
div[style*="position: fixed"][style*="bottom"] {{ display:none !important; }}
div[class*="manage"] {{ display:none !important; }}
section[data-testid="stSidebar"] {{ display:none !important; }}
[data-testid="collapsedControl"] {{ display:none !important; }}
.block-container {{ padding:16px 24px !important; max-width:100% !important; }}

/* ── Mobile responsive ── */
@media (max-width: 768px) {{
    .block-container {{ padding:10px 12px !important; }}
    .metrics-row {{ grid-template-columns:repeat(2,1fr) !important; gap:8px !important; }}
    .metric-val {{ font-size:16px !important; }}
    .metric-lbl {{ font-size:8px !important; }}
    .trade-card {{ padding:12px !important; }}
    .top-row {{ flex-direction:column; align-items:flex-start; gap:8px; }}
    .top-right {{ flex-wrap:wrap; }}
    div[style*="grid-template-columns:80px"] {{
        grid-template-columns:70px 60px 1fr 1fr 1fr !important;
        font-size:11px !important;
    }}
    .hist-hdr, .hist-row {{
        grid-template-columns:90px 60px 1fr 1fr !important;
    }}
    /* Hide less critical columns on mobile */
    div[style*="grid-template-columns:80px"] > span:nth-child(4),
    div[style*="grid-template-columns:80px"] > span:nth-child(7) {{
        display:none !important;
    }}
}}
hr {{ border-color:rgba(0,180,255,0.08) !important; margin:16px 0 !important; }}

/* ── Top bar ── */
.top-row {{
    display:flex; align-items:center; justify-content:space-between;
    margin-bottom:14px;
}}
.dash-title {{ font-size:18px; font-weight:700; color:{TEXT}; display:flex; align-items:center; gap:10px; }}
.live-pill {{
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(0,255,136,0.08); border:1px solid rgba(0,255,136,0.25);
    color:{GREEN}; font-size:9px; font-weight:700; letter-spacing:2px;
    padding:3px 10px; border-radius:20px;
}}
.live-dot {{ width:5px; height:5px; border-radius:50%; background:{GREEN}; animation:blink 1.4s infinite; display:inline-block; }}
.top-right {{ display:flex; align-items:center; gap:10px; }}
.last-update {{ font-size:11px; color:{TEXT3}; }}

/* ── Metric cards ── */
.metrics-row {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:16px; }}
.metric-card {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:12px 14px; position:relative; overflow:hidden; cursor:default;
}}
.metric-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:var(--mc, rgba(0,180,255,0.3));
}}
.metric-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; margin-bottom:4px; }}
.metric-val {{ font-family:'JetBrains Mono',monospace; font-size:20px; font-weight:700; color:{TEXT}; line-height:1.1; }}
.metric-sub {{ font-size:10px; color:{TEXT2}; margin-top:3px; }}

/* ── Tooltip system ── */
.tt {{ position:relative; display:block; cursor:help; }}
.tt .tip {{
    visibility:hidden; opacity:0;
    position:fixed; z-index:99999;
    background:#071828; border:1px solid rgba(0,180,255,0.4);
    border-radius:10px; padding:14px 16px;
    font-size:11px; color:{TEXT}; line-height:1.7;
    width:260px;
    box-shadow:0 16px 48px rgba(0,0,0,0.8), 0 0 0 1px rgba(0,180,255,0.1);
    transition:opacity 0.15s; pointer-events:none;
    text-align:left; white-space:normal;
}}
.tt:hover .tip {{ visibility:visible; opacity:1; }}
/* JS positions the tip on hover to stay on-screen */

/* ── Section header ── */
.sec {{
    font-size:9px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{TEXT3};
    display:flex; align-items:center; gap:10px; margin-bottom:12px;
}}
.sec::after {{ content:''; flex:1; height:1px; background:linear-gradient(90deg, rgba(0,180,255,0.15), transparent); }}
.sec-n {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:{TEXT2}; background:rgba(0,180,255,0.06); border:1px solid rgba(0,180,255,0.12); padding:1px 8px; border-radius:20px; }}

/* ── Trade card ── */
.trade-card {{
    position:relative; padding:16px;
    background:linear-gradient(135deg, rgba(10,26,44,0.97) 0%, rgba(5,12,22,0.97) 100%);
    border:1px solid var(--acc2, rgba(0,180,255,0.15));
    border-radius:8px; overflow:visible; height:100%;
}}
.trade-card::before {{
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg, transparent, var(--acc), transparent); opacity:0.7;
    border-radius:8px 8px 0 0;
}}
.c {{ position:absolute; width:10px; height:10px; }}
.c-tl {{ top:0;left:0; border-top:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:2px 0 0 0; }}
.c-tr {{ top:0;right:0; border-top:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 2px 0 0; }}
.c-bl {{ bottom:0;left:0; border-bottom:2px solid var(--acc); border-left:2px solid var(--acc); border-radius:0 0 0 2px; }}
.c-br {{ bottom:0;right:0; border-bottom:2px solid var(--acc); border-right:2px solid var(--acc); border-radius:0 0 2px 0; }}
.card-ticker {{ font-family:'JetBrains Mono',monospace; font-size:22px; font-weight:700; line-height:1; }}
.card-action {{ font-size:10px; font-weight:800; letter-spacing:2px; padding:4px 10px; border-radius:3px; display:inline-block; margin-top:5px; }}
.card-div {{ height:1px; background:rgba(0,180,255,0.08); margin:10px 0; }}
.stars {{ font-size:15px; letter-spacing:2px; margin-bottom:5px; }}
.card-reason {{
    font-size:11px; color:{TEXT}; line-height:1.5;
    background:rgba(0,0,0,0.25); border-radius:4px; padding:8px 10px;
    border-left:2px solid var(--acc); margin-bottom:10px;
}}
.card-footer {{ display:flex; justify-content:space-between; align-items:center; }}
.card-pos {{ font-family:'JetBrains Mono',monospace; font-size:20px; font-weight:700; }}
.card-pos-lbl {{ font-size:11px; font-weight:600; color:{TEXT2}; margin-bottom:3px; }}
.auto-yes {{
    background:rgba(0,255,136,0.12); border:1px solid rgba(0,255,136,0.35);
    color:{GREEN}; font-size:11px; font-weight:800; letter-spacing:0.5px;
    padding:6px 12px; border-radius:4px; display:inline-block;
}}
.auto-no {{
    background:rgba(0,0,0,0.2); border:1px solid rgba(0,180,255,0.12);
    color:{TEXT2}; font-size:11px; font-weight:600;
    padding:6px 12px; border-radius:4px; display:inline-block;
}}

/* ── Open positions ── */
.pos-row {{
    background:{SURF}; border:1px solid rgba(0,180,255,0.1); border-radius:8px;
    padding:12px 16px; margin-bottom:8px;
    display:grid; grid-template-columns:70px 70px 1fr 1fr 1fr 1fr;
    align-items:center; gap:10px;
    transition:border-color 0.15s;
}}
.pos-row:hover {{ border-color:rgba(0,180,255,0.3); }}
.pos-ticker {{ font-family:'JetBrains Mono',monospace; font-size:15px; font-weight:700; color:{GLOW}; }}
.pos-badge-l {{ background:rgba(0,255,136,0.1); border:1px solid rgba(0,255,136,0.3); color:{GREEN}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-badge-s {{ background:rgba(255,45,120,0.1); border:1px solid rgba(255,45,120,0.3); color:{RED}; font-size:9px; font-weight:800; letter-spacing:1px; padding:2px 7px; border-radius:3px; }}
.pos-col {{ display:flex; flex-direction:column; gap:2px; }}
.pos-lbl {{ font-size:9px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:{TEXT3}; }}
.pos-val {{ font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600; color:{TEXT}; }}

/* ── Activity log ── */
.log-item {{ padding:8px 0; border-bottom:1px solid rgba(0,180,255,0.06); display:flex; gap:12px; align-items:flex-start; }}
.log-item:last-child {{ border-bottom:none; }}
.log-time {{ font-family:'JetBrains Mono',monospace; font-size:10px; color:{TEXT3}; white-space:nowrap; margin-top:1px; width:40px; flex-shrink:0; }}
.log-text {{ font-size:11px; color:{TEXT2}; line-height:1.4; }}
.log-dot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; margin-top:4px; }}

/* ── No data ── */
.waiting {{ padding:50px 20px; text-align:center; }}
.wait-ring {{ width:70px; height:70px; border:2px solid rgba(0,180,255,0.1); border-top:2px solid {GLOW}; border-radius:50%; animation:spin 1.4s linear infinite; margin:0 auto 16px; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.25}} }}

div[data-testid="stSelectbox"] div {{ background:{SURF} !important; border-color:rgba(0,180,255,0.2) !important; color:{TEXT} !important; }}

/* ── Trade history table ── */
.hist-row {{
    display:grid; grid-template-columns:90px 80px 60px 90px 100px 1fr;
    align-items:center; gap:10px;
    padding:10px 16px; border-bottom:1px solid rgba(0,180,255,0.05);
    transition:background 0.1s;
}}
.hist-row:hover {{ background:rgba(0,180,255,0.03); }}
.hist-row:last-child {{ border-bottom:none; }}
.hist-hdr {{ display:grid; grid-template-columns:90px 80px 60px 90px 100px 1fr; gap:10px; padding:8px 16px; background:rgba(0,180,255,0.04); border-radius:6px 6px 0 0; }}
.hist-lbl {{ font-size:9px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEXT3}; }}
.stButton > button {{
    background:rgba(0,180,255,0.08) !important; color:{GLOW} !important;
    border:1px solid rgba(0,180,255,0.25) !important; border-radius:6px !important;
    font-size:12px !important; font-weight:600 !important; padding:6px 18px !important;
    transition:all 0.15s !important;
}}
.stButton > button:hover {{ background:rgba(0,180,255,0.18) !important; border-color:rgba(0,180,255,0.5) !important; }}
</style>
""", unsafe_allow_html=True)

# ── STATIC DATA (predictions — changes 12x/day on weekdays) ──────────────────
# On weekends or before the first scan of the day, fall back to the most
# recent trading day that has data (up to 7 days back). This ensures the
# dashboard always shows the last available scan — never a blank screen.
picks_df       = None
last_scan      = ""
last_scan_date = ""
trades         = []
db_ok          = False

try:
    from db import load_predictions_for_date, load_trades, db_available
    from datetime import timedelta
    db_ok = db_available()
    if db_ok:
        # Try today first, then walk back up to 7 days to find latest data
        for _days_back in range(8):
            _try_date = (datetime.today() - timedelta(days=_days_back)).strftime("%Y-%m-%d")
            rows = load_predictions_for_date(_try_date)
            if rows:
                last_scan_date = _try_date
                picks_df = pd.DataFrame(rows)
                if "created_at" in picks_df.columns:
                    ts = pd.to_datetime(picks_df["created_at"].iloc[0])
                    last_scan = ts.strftime("%H:%M")
                break
        try:
            trades = load_trades()[:20]
        except Exception:
            trades = []
except Exception:
    pass

# ── ALPACA CONFIG (just check credentials once) ────────────────────────────────
try:
    from execution.alpaca import is_configured, is_live_mode
    alpaca_ok = is_configured()
    is_live   = is_live_mode()
except Exception:
    alpaca_ok = False
    is_live   = False

# ── LOADING OVERLAY (shows when refresh is clicked) ───────────────────────────
if st.session_state.get("_refreshing"):
    st.markdown(f"""
    <div style="position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;
                background:rgba(3,6,13,0.90);backdrop-filter:blur(8px);
                display:flex;flex-direction:column;align-items:center;
                justify-content:center;gap:28px;">
      <!-- Outer glow ring -->
      <div style="position:relative;width:90px;height:90px;">
        <div style="position:absolute;inset:0;border-radius:50%;
                    border:2px solid rgba(0,212,255,0.1);"></div>
        <div style="position:absolute;inset:0;border-radius:50%;
                    border:3px solid transparent;
                    border-top:3px solid {GLOW};
                    animation:spin 0.8s linear infinite;"></div>
        <div style="position:absolute;inset:8px;border-radius:50%;
                    border:2px solid transparent;
                    border-top:2px solid {GREEN};
                    animation:spin 1.2s linear infinite reverse;"></div>
        <div style="position:absolute;inset:0;display:flex;align-items:center;
                    justify-content:center;font-size:22px;">⚡</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:16px;font-weight:700;letter-spacing:3px;
                    text-transform:uppercase;color:{GLOW};margin-bottom:8px;">
          Refreshing
        </div>
        <div style="font-size:12px;color:{TEXT2};">
          Pulling latest data from Alpaca &amp; Supabase...
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    import time
    st.cache_data.clear()
    st.cache_resource.clear()
    time.sleep(1.0)
    st.session_state["_refreshing"] = False
    st.rerun()

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
n_auto  = int((picks_df["score"] >= 70).sum()) if picks_df is not None and not picks_df.empty and "score" in picks_df.columns else 0
st.session_state["_n_picks"] = n_picks
st.session_state["_n_auto"]  = n_auto

# ── HELPERS ───────────────────────────────────────────────────────────────────
def stars(score):
    f = round(score / 20)
    return "★" * f + "☆" * (5 - f)

def plain_reason(row):
    sigs   = row.get("signals_triggered", [])
    direct = row.get("direction","mixed")
    vol    = float(row.get("volume_ratio", 0) or 0)
    rsi    = float(row.get("rsi", 50) or 50)
    score  = float(row.get("score", 0))
    if isinstance(sigs, str): sigs = [s.strip() for s in sigs.split(";") if s.strip()]
    parts  = []
    if vol >= 1.5:  parts.append(f"volume is {vol:.1f}× above average")
    if rsi < 35:    parts.append(f"RSI at {rsi:.0f} — oversold, potential bounce")
    elif rsi > 65:  parts.append(f"RSI at {rsi:.0f} — overbought, potential reversal")
    if any("BB" in s or "squeeze" in s.lower() for s in sigs):
        parts.append("Bollinger Band squeeze — low volatility breakout incoming")
    if score >= 70: parts.append(f"AI model has high confidence ({score:.0f}/100) in this setup")
    elif score >= 50: parts.append(f"AI model sees a moderate edge ({score:.0f}/100)")
    if not parts: parts.append(f"Multiple technical signals align for a {direct} move")
    return ". ".join(p.capitalize() for p in parts[:3]) + "."

def tooltip_content(row):
    score  = float(row.get("score", 0))
    rsi    = float(row.get("rsi", 0) or 0)
    vol    = float(row.get("volume_ratio", 0) or 0)
    bb     = float(row.get("bb_pct", 0) or 0)
    sent   = float(row.get("sentiment_score", 0) or 0)
    xgb    = float(row.get("xgb_prob", 0) or 0)
    dur    = row.get("duration", "—")
    sigs   = row.get("signals_triggered", [])
    if isinstance(sigs, str): sigs = [s.strip() for s in sigs.split(";") if s.strip()]
    lines = [
        f"<b style='color:#00d4ff;'>Technical Details</b>",
        f"Score: {score:.0f}/100",
        f"RSI: {rsi:.1f}",
        f"Volume ratio: {vol:.1f}×",
        f"BB squeeze: {bb:.2f}",
        f"Sentiment: {sent:+.3f}",
        f"XGBoost prob: {xgb:.0%}" if xgb else "",
        f"Window: {dur}",
        f"<br><b style='color:#00d4ff;'>Signals triggered:</b>",
    ] + [f"• {_html.escape(s)}" for s in sigs[:4]]
    return "<br>".join(l for l in lines if l)

def ring(score, acc, sz=62):
    r = sz//2 - 7; cx = cy = sz//2
    circ = 2*math.pi*r; off = circ*(1-score/100)
    c = GREEN if score>=70 else AMBER if score>=50 else TEXT2
    fs = max(11, sz//5)
    return (
        f'<svg width="{sz}" height="{sz}" viewBox="0 0 {sz} {sz}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(0,180,255,0.08)" stroke-width="5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="5"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 {cx} {cy})"'
        f' style="filter:drop-shadow(0 0 5px {c});"/>'
        f'<text x="{cx}" y="{cy+fs//3}" text-anchor="middle" fill="{c}"'
        f' font-size="{fs}" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'</svg>'
    )

# ── HEADER (static) ───────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    mode_badge = (
        f'<span style="background:rgba(255,45,120,0.15);border:1px solid rgba(255,45,120,0.4);color:{RED};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">🔴 LIVE TRADING</span>'
        if (alpaca_ok and is_live) else
        f'<span style="background:rgba(255,170,0,0.1);border:1px solid rgba(255,170,0,0.3);color:{AMBER};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">PAPER MODE</span>'
        if alpaca_ok else
        f'<span style="background:rgba(0,0,0,0.2);border:1px solid {TEXT3};color:{TEXT3};font-size:9px;font-weight:800;letter-spacing:2px;padding:2px 8px;border-radius:3px;">ALPACA OFF</span>'
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
        f'<span style="font-size:18px;font-weight:700;color:{TEXT};">🔺 ILLUMINATI</span>'
        f'<span class="live-pill"><span class="live-dot"></span>LIVE</span>'
        f'{mode_badge}'
        f'<span style="font-size:11px;color:{TEXT3};">Last scan: {last_scan if last_scan else "pending"} &nbsp;·&nbsp; '
        f'{"Today" if last_scan_date == datetime.today().strftime("%Y-%m-%d") else ("⚠ " + datetime.strptime(last_scan_date, "%Y-%m-%d").strftime("%a %b %d") + " (last trading day)") if last_scan_date else datetime.today().strftime("%b %d %Y")}'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True)
with hc2:
    if st.button("⟳  Refresh", use_container_width=True, key="refresh_btn"):
        st.session_state["_refreshing"] = True
        st.rerun()

# ── MARKET REGIME STRIP ───────────────────────────────────────────────────────
try:
    from signals.market_regime import get_market_regime
    _regime = get_market_regime()
    _r_icon  = {"bull": "🟢", "neutral": "🟡", "bear": "🔴"}.get(_regime["regime"], "⚪")
    _r_color = {"bull": GREEN, "neutral": AMBER, "bear": RED}.get(_regime["regime"], TEXT3)
    _r_bg    = {"bull": "rgba(0,255,136,0.06)", "neutral": "rgba(255,170,0,0.06)",
                "bear": "rgba(255,45,120,0.06)"}.get(_regime["regime"], "rgba(255,255,255,0.03)")

    _spy_pct = _regime.get("spy_vs_200ma_pct", 0)
    _spy_col = GREEN if _spy_pct > 2 else RED if _spy_pct < -2 else AMBER
    _vix     = _regime.get("vix", 0)
    _vix_col = GREEN if _vix < 20 else AMBER if _vix < 30 else RED
    _secs    = _regime.get("sectors_above_50ma", 0)
    _warn    = _regime.get("warning", "")

    _regime_html = (
        f'<div style="display:flex;align-items:center;gap:16px;padding:8px 14px;'
        f'background:{_r_bg};border:1px solid {_r_color}22;border-radius:7px;margin-bottom:12px;'
        f'font-size:11px;flex-wrap:wrap;">'
        f'<span style="font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:{_r_color};">'
        f'{_r_icon} {_regime["regime"].upper()} REGIME</span>'
        f'<span style="color:{TEXT3};">|</span>'
        f'<span style="color:{TEXT3};">VIX</span>&nbsp;<span style="color:{_vix_col};font-family:JetBrains Mono,monospace;font-weight:700;">{_vix:.1f}</span>'
        f'<span style="color:{TEXT3};">|</span>'
        f'<span style="color:{TEXT3};">SPY vs 200MA</span>&nbsp;<span style="color:{_spy_col};font-family:JetBrains Mono,monospace;font-weight:700;">{_spy_pct:+.1f}%</span>'
        f'<span style="color:{TEXT3};">|</span>'
        f'<span style="color:{TEXT3};">Sectors above 50MA</span>&nbsp;<span style="color:{TEXT};font-family:JetBrains Mono,monospace;font-weight:700;">{_secs}/11</span>'
        + (f'<span style="color:{TEXT3};">|</span><span style="color:{AMBER};">⚠ {_warn}</span>' if _warn else "")
        + f'</div>'
    )
    st.markdown(_regime_html, unsafe_allow_html=True)
except Exception:
    pass   # regime check is non-blocking

# ── LIVE FRAGMENT: portfolio strip + positions (auto-refreshes every 30s) ──────

def _get_alpaca_clock() -> dict:
    """
    Fetch market status directly from Alpaca's clock endpoint.
    Always use Alpaca — never compute market hours manually.
    Returns: {is_open, next_open, next_close, timestamp}
    """
    try:
        from execution.alpaca import _get_client
        client = _get_client()
        clock  = client.get_clock()
        return {
            "is_open":    clock.is_open,
            "next_open":  clock.next_open,
            "next_close": clock.next_close,
            "timestamp":  clock.timestamp,
        }
    except Exception:
        return {"is_open": None, "next_open": None, "next_close": None, "timestamp": None}


def _market_clock() -> str:
    """Current ET time from Alpaca clock."""
    try:
        clk = _get_alpaca_clock()
        ts  = clk.get("timestamp")
        if ts:
            from zoneinfo import ZoneInfo
            et = ts.astimezone(ZoneInfo("America/New_York"))
            return et.strftime("%I:%M %p ET")
    except Exception:
        pass
    return datetime.utcnow().strftime("%H:%M UTC")


def _is_market_open() -> bool:
    """True if Alpaca says market is currently open."""
    clk = _get_alpaca_clock()
    return bool(clk.get("is_open"))


def _market_status() -> str:
    """Market status + countdown from Alpaca clock — never computed manually."""
    try:
        clk      = _get_alpaca_clock()
        is_open  = clk.get("is_open")
        ts       = clk.get("timestamp")
        nxt_open = clk.get("next_open")
        nxt_cls  = clk.get("next_close")

        if ts is None:
            return "Status unknown"

        if is_open:
            if nxt_cls:
                diff   = int((nxt_cls - ts).total_seconds())
                h, rem = divmod(diff, 3600)
                m      = rem // 60
                closes = f"closes in {h}h {m}m" if h else f"closes in {m}m"
            else:
                closes = "open"
            return f"🟢 Open · {closes}"
        else:
            if nxt_open:
                diff   = int((nxt_open - ts).total_seconds())
                h, rem = divmod(diff, 3600)
                m      = rem // 60
                opens  = f"opens in {h}h {m}m" if h else f"opens in {m}m"
            else:
                opens = "soon"
            from zoneinfo import ZoneInfo
            et = ts.astimezone(ZoneInfo("America/New_York"))
            if et.weekday() >= 5:
                return f"Weekend · {opens}"
            return f"Closed · {opens}"
    except Exception:
        return "Status unknown"

def _next_scan_label() -> str:
    """Returns human-readable label for the next scheduled scan + countdown."""
    try:
        from zoneinfo import ZoneInfo
        from datetime import timezone
        ET = ZoneInfo("America/New_York")
        now = datetime.now(ET)

        # All 12 daily scan times (hour, minute) in ET
        SCAN_TIMES = [(7,0),(8,0),(9,0),(9,30),(10,30),(11,0),(12,0),(13,0),(14,0),(15,0),(15,30),(16,0)]

        # Build today's scan datetimes
        today_scans = [
            now.replace(hour=h, minute=m, second=0, microsecond=0)
            for h, m in SCAN_TIMES
        ]
        future = [s for s in today_scans if s > now]

        if future:
            nxt  = future[0]
            diff = int((nxt - now).total_seconds())
            h, m = divmod(diff // 60, 60)
            countdown = f"in {h}h {m}m" if h else f"in {m}m"
            hour = nxt.hour % 12 or 12
            return f"{hour}:{nxt.strftime('%M %p')} ET · {countdown}"
        else:
            # All done today — show tomorrow's first scan
            from datetime import timedelta
            tomorrow = (now + timedelta(days=1)).replace(hour=7, minute=0, second=0)
            diff = int((tomorrow - now).total_seconds())
            h = diff // 3600
            return f"Tomorrow 7:00 AM ET · in {h}h"
    except Exception:
        return "7AM · 9AM · 10:30AM · 12PM · 2PM · 3:30PM · 4PM ET"


@st.fragment(run_every=30)
def live_alpaca():
    """Fetches fresh Alpaca data every 30 seconds — P&L, equity, positions."""
    from calendar import monthrange
    acct      = {"portfolio_value": 0, "buying_power": 0, "cash": 0}
    positions = []
    try:
        from execution.alpaca import get_account, get_positions, _get_client
        if alpaca_ok:
            acct      = get_account()
            positions = get_positions()
    except Exception:
        pass

    # Re-read pick counts from session state so they reflect latest scan
    _n_picks = st.session_state.get("_n_picks", n_picks)
    _n_auto  = st.session_state.get("_n_auto",  n_auto)

    portfolio    = acct.get("portfolio_value", 0)
    buying_power = acct.get("buying_power", 0)
    equity       = acct.get("equity", portfolio)
    total_pl     = sum(p.get("unrealized_pl", 0) for p in positions)
    pl_color     = GREEN if total_pl >= 0 else RED
    # store for goal bar + trade history P&L lookup
    st.session_state["_live_pl"]             = total_pl
    st.session_state["_live_positions"]      = len(positions)
    st.session_state["_live_positions_data"] = positions
    st.session_state["_portfolio_value"]     = portfolio  # for goal bar target calc

    # Store realized P&L for goal bar (equity - last_equity - unrealized = realized)
    _last_eq   = acct.get("last_equity", portfolio)
    _daily_pnl = portfolio - _last_eq
    st.session_state["_realized_pl"] = _daily_pnl - total_pl

    # ── Metric strip ──────────────────────────────────────────────────────────
    def mc(label, val, sub, color=TEXT3, tip=""):
        tip_html = f'<div class="tip">{tip}</div>' if tip else ""
        return (
            f'<div class="metric-card tt" style="--mc:{color}44;">'
            f'<div class="metric-lbl">{label}</div>'
            f'<div class="metric-val" style="color:{color};">{val}</div>'
            f'<div class="metric-sub">{sub}</div>'
            f'{tip_html}</div>'
        )

    # ── ALL P&L NUMBERS COME STRAIGHT FROM ALPACA — NO LOCAL MATH ──
    # P&L Today = Alpaca's portfolio_history(period='1D').profit_loss[-1]
    #   This is THE number Alpaca shows as "Today's Gain" in their own app.
    # Open Now = sum of position.unrealized_pl from Alpaca positions endpoint.
    # Closed Today = P&L Today minus Open Now (the only derived value, but
    #   both inputs are direct from Alpaca — no fill matching, no guessing).
    _unrealized_pl = total_pl  # from get_positions() → sums Alpaca's position.unrealized_pl

    try:
        from alpaca.trading.requests import GetPortfolioHistoryRequest as _GPH
        _hist_today = _get_client().get_portfolio_history(
            _GPH(period="1D", timeframe="1H"))
        # Alpaca's authoritative today-from-market-open P&L
        _pl_arr = [v for v in (_hist_today.profit_loss or []) if v is not None]
        _total_today = float(_pl_arr[-1]) if _pl_arr else (portfolio - acct.get("last_equity", portfolio))
    except Exception:
        # Fallback: simple equity diff (still Alpaca-direct)
        _total_today = portfolio - acct.get("last_equity", portfolio)

    # Closed Today = Today's P&L − currently floating unrealized
    # (both pulled straight from Alpaca — no fill matching)
    _realized_today = _total_today - _unrealized_pl

    _total_sign  = "+" if _total_today    >= 0 else ""
    _total_color = GREEN if _total_today  > 0 else RED if _total_today  < 0 else TEXT2
    _ul_color    = GREEN if _unrealized_pl > 0 else RED if _unrealized_pl < 0 else TEXT2
    _ul_sign     = "+" if _unrealized_pl  >= 0 else ""
    _rl_color    = GREEN if _realized_today > 0 else RED if _realized_today < 0 else TEXT2
    _rl_sign     = "+" if _realized_today  >= 0 else ""
    _tot_sign    = _total_sign

    # All-time P&L = portfolio vs actual account starting equity (from Alpaca history)
    # Cached in session state — only fetched once per session to avoid API overhead
    if "account_start_equity" not in st.session_state:
        try:
            from alpaca.trading.requests import GetPortfolioHistoryRequest
            _hist = _get_client().get_portfolio_history(
                GetPortfolioHistoryRequest(period="1M", timeframe="1D"))
            _equities = [e for e in (_hist.equity or []) if e and e > 0]
            st.session_state["account_start_equity"] = _equities[0] if _equities else portfolio
        except Exception:
            st.session_state["account_start_equity"] = portfolio

    _start_equity  = st.session_state["account_start_equity"]
    _alltime_pl    = portfolio - _start_equity
    _alltime_color = GREEN if _alltime_pl > 0 else RED if _alltime_pl < 0 else TEXT2
    _alltime_sign  = "+" if _alltime_pl >= 0 else ""

    st.markdown(
        f'<div class="metrics-row" style="grid-template-columns:repeat(8,1fr);">'
        + mc("Portfolio Value",
             f"${portfolio:,.0f}", "Total equity",
             GLOW, "Total Alpaca account value — cash + open positions.")
        + mc("Total P&L",
             f"{_alltime_sign}${abs(_alltime_pl):,.2f}", "Since account started",
             _alltime_color,
             f"All-time profit vs starting equity of ${_start_equity:,.0f} (from Alpaca history).")
        + mc("P&L Today",
             f"{_tot_sign}${abs(_total_today):,.2f}", "Direct from Alpaca",
             _total_color,
             "Alpaca's official today-from-market-open P&L (portfolio_history API). Same number Alpaca shows in their app.")
        + mc("Closed Today",
             f"{_rl_sign}${abs(_realized_today):,.2f}", "P&L Today − Open Now",
             _rl_color,
             "Realized portion = Today's total P&L (Alpaca) minus current unrealized (Alpaca). No fill matching.")
        + mc("Open Now",
             f"{_ul_sign}${abs(_unrealized_pl):,.2f}",
             f"{len(positions)} position{'s' if len(positions) != 1 else ''} live",
             _ul_color,
             "Sum of position.unrealized_pl direct from Alpaca positions endpoint.")
        + mc("Buying Power",
             f"${buying_power:,.0f}", "Available now",
             TEXT, "Cash available for new positions right now.")
        + mc("AI Setups Today",
             str(_n_picks) if _n_picks else "—", "Score ≥ 50",
             GREEN if _n_picks else TEXT2,
             "Tickers flagged today. Agent scans 12× daily.")
        + mc("Market Clock",
             _market_clock(), _market_status(),
             GREEN if _is_market_open() else RED,
             "Market status from Alpaca. GREEN = open.")
        + f'</div>',
        unsafe_allow_html=True)

    # ── Open positions ────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Section header + Close All button on same row
    sec_col, btn_col = st.columns([5, 1])
    with sec_col:
        st.markdown(
            f'<div class="sec">Open Positions <span class="sec-n">{len(positions)}</span>'
            f'<span style="font-size:9px;color:{TEXT3};margin-left:8px;">· updates every 30s</span></div>',
            unsafe_allow_html=True)
    with btn_col:
        if positions and st.button("⚡ Close All", use_container_width=True,
                                   key="close_all_btn",
                                   help="Close all open positions at market price"):
            st.session_state["confirm_close_all"] = True
            st.rerun()

    # ── Confirm close all ─────────────────────────────────────────────────────
    if "confirm_close_all" not in st.session_state:
        st.session_state["confirm_close_all"] = False

    if st.session_state.get("confirm_close_all"):
        total_pl = sum(p.get("unrealized_pl", 0) for p in positions)
        pl_color = GREEN if total_pl >= 0 else RED
        pl_sign  = "+" if total_pl >= 0 else ""
        st.markdown(
            f'<div style="background:rgba(255,45,120,0.10);border:1px solid rgba(255,45,120,0.4);'
            f'border-radius:8px;padding:16px 20px;margin-bottom:14px;">'
            f'<div style="font-size:14px;font-weight:700;color:{RED};margin-bottom:6px;">'
            f'⚠ Close ALL {len(positions)} positions at market price?</div>'
            f'<div style="font-size:12px;color:{TEXT2};">Current unrealized P&L: '
            f'<span style="color:{pl_color};font-family:JetBrains Mono,monospace;font-weight:700;">'
            f'{pl_sign}${abs(total_pl):,.2f}</span> · This cannot be undone.</div>'
            f'</div>',
            unsafe_allow_html=True)
        ca1, ca2, ca3, ca4 = st.columns([3, 1, 1, 1])
        with ca2:
            if st.button("✓ Close All", type="primary", use_container_width=True,
                         key="confirm_close_all_yes"):
                from execution.alpaca import close_position, get_positions
                import time as _t
                closed, failed = [], []
                with st.spinner(f"Closing {len(positions)} positions..."):
                    # First pass — close all positions
                    for p in positions:
                        try:
                            r = close_position(p["ticker"])
                            if r.get("status") == "closed":
                                closed.append(p["ticker"])
                            else:
                                failed.append(p["ticker"])
                        except Exception:
                            failed.append(p["ticker"])

                    # Second pass — wait then retry anything still open (handles
                    # race conditions where shares were briefly held by stale orders)
                    if failed:
                        _t.sleep(2)
                        still_open = {pp["ticker"] for pp in get_positions()}
                        retry_list = [t for t in failed if t in still_open]
                        for tk in retry_list:
                            try:
                                r = close_position(tk)
                                if r.get("status") == "closed":
                                    failed.remove(tk)
                                    closed.append(tk)
                            except Exception:
                                pass

                    # Third pass — final retry after another wait
                    if failed:
                        _t.sleep(2)
                        still_open = {pp["ticker"] for pp in get_positions()}
                        retry_list = [t for t in failed if t in still_open]
                        for tk in retry_list:
                            try:
                                r = close_position(tk)
                                if r.get("status") == "closed":
                                    failed.remove(tk)
                                    closed.append(tk)
                            except Exception:
                                pass

                st.session_state["confirm_close_all"] = False
                if closed:
                    st.success(f"✓ Closed {len(closed)} positions: {', '.join(closed)}")
                if failed:
                    st.error(f"Still stuck after 3 retries: {', '.join(failed)} — try clicking Close All again")
                st.rerun()
        with ca3:
            if st.button("✗ Cancel", use_container_width=True, key="confirm_close_all_no"):
                st.session_state["confirm_close_all"] = False
                st.rerun()

    # Confirmation state (single position)
    if "confirm_close" not in st.session_state:
        st.session_state["confirm_close"] = None

    if st.session_state["confirm_close"]:
        ticker_to_close = st.session_state["confirm_close"]
        st.markdown(
            f'<div style="background:rgba(255,45,120,0.08);border:1px solid rgba(255,45,120,0.3);'
            f'border-radius:8px;padding:14px 18px;margin-bottom:12px;">'
            f'<span style="color:{TEXT};font-size:13px;">⚠ Close <strong style="color:{RED};">'
            f'{ticker_to_close}</strong> at market price right now?</span></div>',
            unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns([3, 1, 1])
        with cc2:
            if st.button("✓ Yes, close it", type="primary", use_container_width=True, key="confirm_yes"):
                try:
                    from execution.alpaca import close_position
                    result = close_position(ticker_to_close)
                    st.success(f"{ticker_to_close} closed." if result.get("status") == "closed"
                               else f"Error: {result.get('reason')}")
                except Exception as e:
                    st.error(str(e))
                st.session_state["confirm_close"] = None
                st.rerun()
        with cc3:
            if st.button("✗ Cancel", use_container_width=True, key="confirm_no"):
                st.session_state["confirm_close"] = None
                st.rerun()

    if positions:
        _trade_sl_tp      = {}
        _trailing_tickers = set()
        _today_str        = ""

        try:
            from datetime import date as _date, datetime as _dt, timezone as _tz, timedelta as _td
            _today_str = _date.today().isoformat()

            if alpaca_ok:
                from execution.alpaca import _get_client as _aclient
                from alpaca.trading.requests import GetOrdersRequest
                from alpaca.trading.enums import QueryOrderStatus

                _client_inst = _aclient()

                # ── Entry dates: read directly from Alpaca filled buy orders ──
                # Source of truth — avoids stale Supabase trades table entries
                _after = (_dt.now(_tz.utc) - _td(days=60)).strftime("%Y-%m-%dT00:00:00Z")
                _all_orders = _client_inst.get_orders(
                    GetOrdersRequest(status=QueryOrderStatus.ALL,
                                     after=_after, limit=500))
                for _o in _all_orders:
                    if "buy" not in str(getattr(_o, "side", "")).lower():
                        continue
                    if str(getattr(_o, "status", "")) not in ("filled", "partially_filled"):
                        continue
                    if not _o.filled_at:
                        continue
                    _sym = _o.symbol
                    _filled_date = str(_o.filled_at)[:10]  # YYYY-MM-DD
                    # Keep the most recent fill per ticker
                    if ("entry_ts" not in _trade_sl_tp.get(_sym, {})
                            or _filled_date > _trade_sl_tp[_sym].get("entry_ts", "")):
                        _trade_sl_tp.setdefault(_sym, {})["entry_ts"] = _filled_date

                # Trailing tickers now come from get_positions() via is_trailing field
                # (no separate order query needed)

        except Exception:
            pass

        # ── SL/TP fallback from Supabase trades table ──
        try:
            _recent_trades = load_trades()[:50] if db_ok else []
            for _t in _recent_trades:
                _tk = _t.get("ticker", "")
                if not _tk:
                    continue
                _trade_sl_tp.setdefault(_tk, {})
                if _t.get("stop_loss") and _t.get("take_profit"):
                    if "stop_loss" not in _trade_sl_tp[_tk]:
                        _trade_sl_tp[_tk]["stop_loss"]  = float(_t["stop_loss"])
                    if "take_profit" not in _trade_sl_tp[_tk]:
                        _trade_sl_tp[_tk]["take_profit"] = float(_t["take_profit"])
        except Exception:
            pass

        _GRID = "80px 76px 55px 70px 1fr 1fr 1fr 1fr 1fr"

        # Column header row
        st.markdown(
            f'<div style="display:grid;grid-template-columns:{_GRID} 70px;'
            f'gap:0 16px;padding:6px 14px;border-radius:6px 6px 0 0;'
            f'background:rgba(0,180,255,0.04);margin-bottom:1px;">'
            + "".join(f'<span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
                      f'text-transform:uppercase;color:{TEXT3};">{h}</span>'
                      for h in ["Ticker","Type","Side","Shares","Entry","Current","Stop Loss","Take Profit","P&L",""])
            + f'</div>',
            unsafe_allow_html=True
        )

        # Sort: biggest winners first, biggest losers last
        positions = sorted(positions, key=lambda p: p.get("unrealized_pl", 0), reverse=True)

        _pos_tickers = tuple(p["ticker"] for p in positions)
        _pos_names   = _get_company_names(_pos_tickers)  # module-level cached fn

        for p in positions:
            pl       = p.get("unrealized_pl", 0)
            plpct    = p.get("unrealized_pl_pct", 0)
            pc       = GREEN if pl >= 0 else RED
            arrow    = "▲" if pl >= 0 else "▼"
            raw_side = str(p.get("side","")).lower()
            is_long  = "long" in raw_side or "buy" in raw_side
            side_lbl = "LONG" if is_long else "SHORT"
            side_c   = f"rgba(0,255,136,0.12)" if is_long else f"rgba(255,45,120,0.12)"
            side_bc  = f"rgba(0,255,136,0.3)"  if is_long else f"rgba(255,45,120,0.3)"
            side_tc  = GREEN if is_long else RED
            entry    = p.get("avg_entry_price", 0)
            current  = p.get("current_price", 0)
            ticker_p = p["ticker"]

            # SL/TP — from get_positions() (which reads live Alpaca orders),
            # with Supabase trades table as last-resort fallback
            sl = p.get("stop_loss") or _trade_sl_tp.get(ticker_p, {}).get("stop_loss")
            tp = p.get("take_profit") or _trade_sl_tp.get(ticker_p, {}).get("take_profit")
            is_trailing = p.get("is_trailing", ticker_p in _trailing_tickers)

            # % distance from current price to SL / TP
            def _pct_dist(level, cur, pos_side):
                if not level or not cur:
                    return ""
                if pos_side == "long":
                    sl_d  = (cur - level) / cur * 100   # SL below current
                    tp_d  = (level - cur) / cur * 100   # TP above current
                else:
                    sl_d  = (level - cur) / cur * 100   # SL above current
                    tp_d  = (cur - level) / cur * 100   # TP below current
                return sl_d if level < cur and pos_side == "long" else (
                    tp_d if (pos_side == "long" and level > cur) else (
                    sl_d if pos_side == "short" and level > cur else tp_d))

            _cur = float(current) if current else 0
            if _cur and sl:
                _sl_f = float(sl)
                sl_pct_val = ((_cur - _sl_f) / _cur * 100) if is_long else ((_sl_f - _cur) / _cur * 100)
                sl_pct_str = (f'<span style="font-size:11px;font-weight:600;'
                              f'color:{RED};margin-left:5px;">-{abs(sl_pct_val):.1f}%</span>')
            else:
                sl_pct_str = ""
            if _cur and tp:
                _tp_f = float(tp)
                tp_pct_val = ((_tp_f - _cur) / _cur * 100) if is_long else ((_cur - _tp_f) / _cur * 100)
                tp_pct_str = (f'<span style="font-size:11px;font-weight:600;'
                              f'color:{GREEN};margin-left:5px;">+{abs(tp_pct_val):.1f}%</span>')
            else:
                tp_pct_str = ""

            # Locked profit — show on ANY position where stop is above entry (long)
            # or below entry (short). Works for both trailing and fixed stops.
            _lock_str = ""
            if sl and entry:
                _sl_f  = float(sl)
                _ent_f = float(entry)
                _qty_f = abs(float(p.get("qty", 0)))
                if is_long and _sl_f > _ent_f:
                    _locked_pp = (_sl_f - _ent_f) * _qty_f
                    _lock_str = (
                        f'<span style="display:block;font-size:10px;font-weight:700;'
                        f'letter-spacing:0.4px;color:{GREEN};margin-top:2px;">'
                        f'🔐 LOCKED +${_locked_pp:,.0f}</span>'
                    )
                elif not is_long and _sl_f < _ent_f:
                    _locked_pp = (_ent_f - _sl_f) * _qty_f
                    _lock_str = (
                        f'<span style="display:block;font-size:10px;font-weight:700;'
                        f'letter-spacing:0.4px;color:{GREEN};margin-top:2px;">'
                        f'🔐 LOCKED +${_locked_pp:,.0f}</span>'
                    )

            if is_trailing:
                sl_val = f'${sl:.2f}' if sl else "tracking"
                sl_str = (
                    f'<span style="color:{AMBER};font-family:JetBrains Mono,monospace;'
                    f'font-size:13px;font-weight:700;">🔒 {sl_val}</span>{sl_pct_str}'
                    f'<span style="display:block;font-size:9px;color:{AMBER};'
                    f'letter-spacing:0.8px;font-weight:700;margin-top:1px;">TRAILING</span>'
                    + _lock_str
                )
            elif sl:
                sl_str = (
                    f'<span style="color:{RED};font-family:JetBrains Mono,monospace;'
                    f'font-size:13px;font-weight:600;">${sl:.2f}</span>{sl_pct_str}'
                    + _lock_str
                )
            else:
                sl_str = f'<span style="color:{TEXT3};">—</span>'
            tp_str = (
                f'<span style="color:{GREEN};font-family:JetBrains Mono,monospace;'
                f'font-size:13px;font-weight:600;">${tp:.2f}</span>{tp_pct_str}'
                if tp else f'<span style="color:{TEXT3};">—</span>'
            )

            # Trade type badge — intraday (opened today) vs swing (opened earlier)
            entry_ts = _trade_sl_tp.get(ticker_p, {}).get("entry_ts", "")
            if entry_ts == _today_str:
                type_lbl = "INTRADAY"
                type_bg  = "rgba(255,170,0,0.12)"
                type_bc  = "rgba(255,170,0,0.4)"
                type_tc  = AMBER
            else:
                try:
                    from datetime import datetime as _dt
                    days_held = (_dt.today() - _dt.fromisoformat(entry_ts)).days if entry_ts else 0
                    day_str   = f" · D{days_held}" if days_held > 0 else ""
                except Exception:
                    day_str = ""
                type_lbl = f"SWING{day_str}"
                type_bg  = "rgba(0,212,255,0.08)"
                type_bc  = "rgba(0,212,255,0.3)"
                type_tc  = GLOW

            type_badge = (
                f'<span style="background:{type_bg};border:1px solid {type_bc};color:{type_tc};'
                f'font-size:8px;font-weight:800;letter-spacing:0.8px;padding:2px 6px;'
                f'border-radius:3px;white-space:nowrap;">{type_lbl}</span>'
            )

            row_col, btn_col = st.columns([9, 1])
            with row_col:
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:{_GRID};'
                    f'gap:0 16px;align-items:center;padding:10px 14px;'
                    f'background:{SURF};border:1px solid rgba(0,180,255,0.08);'
                    f'border-radius:6px;margin-bottom:4px;transition:border-color 0.15s;">'
                    f'<span><a href="https://finance.yahoo.com/quote/{ticker_p}" target="_blank" '
                    f'style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
                    f'color:{GLOW};text-decoration:none;cursor:pointer;" '
                    f'onmouseover="this.style.textDecoration=\'underline\'" '
                    f'onmouseout="this.style.textDecoration=\'none\'">{ticker_p}</a>'
                    f'<div style="font-size:9px;color:{TEXT3};margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:78px;">{_pos_names.get(ticker_p,"")}</div></span>'
                    f'<span>{type_badge}</span>'
                    f'<span style="background:{side_c};border:1px solid {side_bc};color:{side_tc};'
                    f'font-size:9px;font-weight:800;letter-spacing:1px;padding:2px 6px;border-radius:3px;">{side_lbl}</span>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:{TEXT};">{p["qty"]:.0f}</span>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:{TEXT2};">${entry:.2f}</span>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:{TEXT};">${current:.2f}</span>'
                    f'<span>{sl_str}</span>'
                    f'<span>{tp_str}</span>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:{pc};">'
                    f'{arrow} ${abs(pl):,.2f} <span style="font-size:11px;font-weight:400;">({abs(plpct):.1f}%)</span></span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with btn_col:
                if st.button("✗ Close", key=f"close_{ticker_p}", use_container_width=True):
                    st.session_state["confirm_close"] = ticker_p
                    st.rerun()
    elif alpaca_ok:
        st.markdown(
            f'<div style="color:{TEXT3};font-size:13px;padding:12px 0;">'
            f'No open positions. Next auto-trade runs when agent finds a setup with score ≥ 70.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="color:{TEXT3};font-size:13px;padding:12px 0;">'
            f'Alpaca not connected — add API keys to enable trading.</div>',
            unsafe_allow_html=True)

live_alpaca()

# ── MAIN CONTENT ──────────────────────────────────────────────────────────────

# ── Horizontal Agent Status + Recent Trades bar (compact, no wasted vertical space) ──
_status_items = [
    (GREEN if last_scan else TEXT3, "Scan",     f"Last run {last_scan}" if last_scan else "No scan today yet"),
    (GREEN if db_ok else RED,       "DB",       "Supabase connected" if db_ok else "Database offline"),
    (GREEN if alpaca_ok else RED,   "Alpaca",   "API connected" if alpaca_ok else "Not configured"),
    (AMBER,                         "Next Scan", _next_scan_label()),
]
_status_html = ""
for _color, _lbl, _val in _status_items:
    _status_html += (
        f'<div style="display:flex;align-items:center;gap:10px;flex:1;min-width:170px;padding:0 12px;'
        f'border-right:1px solid rgba(0,180,255,0.08);">'
        f'<div style="width:8px;height:8px;border-radius:50%;background:{_color};'
        f'box-shadow:0 0 8px {_color};flex-shrink:0;"></div>'
        f'<div style="line-height:1.3;overflow:hidden;">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{TEXT3};">{_lbl}</div>'
        f'<div style="font-size:12px;color:{TEXT};font-family:JetBrains Mono,monospace;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_val}</div>'
        f'</div></div>'
    )

# Recent trades inline (horizontal scrolling pills)
_trades_html = ""
if trades:
    for _t in trades[:10]:
        _side = _t.get("side", "")
        _c    = GREEN if _side == "buy" else RED
        _ts   = str(_t.get("timestamp", ""))[11:16]
        _amt  = float(_t.get("dollar_amount", 0))
        _trades_html += (
            f'<div style="display:flex;align-items:center;gap:6px;padding:4px 10px;'
            f'background:rgba(0,180,255,0.04);border:1px solid rgba(0,180,255,0.1);'
            f'border-radius:6px;white-space:nowrap;font-size:11px;">'
            f'<span style="color:{TEXT3};font-family:JetBrains Mono,monospace;">{_ts}</span>'
            f'<span style="color:{_c};font-weight:700;font-family:JetBrains Mono,monospace;">{_t.get("ticker","")}</span>'
            f'<span style="color:{TEXT2};">{_side.upper()}</span>'
            f'<span style="color:{TEXT};font-family:JetBrains Mono,monospace;">${_amt:,.0f}</span>'
            f'</div>'
        )
else:
    _trades_html = f'<div style="color:{TEXT3};font-size:11px;padding:6px 12px;">No trades yet</div>'

st.markdown(
    f'<div style="display:flex;gap:0;background:{SURF};border:1px solid rgba(0,180,255,0.12);'
    f'border-radius:8px;padding:10px 6px;margin-bottom:14px;align-items:center;">'
    f'<div style="display:flex;flex:0 0 auto;align-items:center;">'
    f'<div style="padding:0 14px;font-size:9px;font-weight:700;letter-spacing:1.5px;'
    f'text-transform:uppercase;color:{GLOW};white-space:nowrap;">AGENTS</div>'
    f'{_status_html}'
    f'</div>'
    f'<div style="padding:0 14px;font-size:9px;font-weight:700;letter-spacing:1.5px;'
    f'text-transform:uppercase;color:{GLOW};white-space:nowrap;border-left:1px solid rgba(0,180,255,0.12);">RECENT</div>'
    f'<div style="display:flex;gap:6px;overflow-x:auto;flex:1;min-width:0;padding:0 4px;">'
    f'{_trades_html}'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

# ── Trade recommendations (full width, scrollable container) ──
st.markdown(
    f'<div class="sec">Today\'s Trade Recommendations <span class="sec-n">{n_picks} setups</span></div>',
    unsafe_allow_html=True)

if picks_df is not None and not picks_df.empty:
    sorted_df = picks_df[
        (picks_df["direction"] != "mixed") &
        (picks_df["score"] >= 70)
    ].sort_values("score", ascending=False)

    # Pre-fetch company names — uses module-level cached function
    _visible_tickers = tuple(sorted_df["ticker"].tolist())
    _cnames = _get_company_names(_visible_tickers)

    # All cards in one scrollable container — 3 rows of 4 visible, scroll for the rest

    def _render_chunk_rows(df_to_render):
        """Render trade cards in rows of 4."""
        _chunks = [df_to_render.iloc[i:i+4] for i in range(0, len(df_to_render), 4)]
        for chunk in _chunks:
            cols = st.columns(4)
            for ci, (_, row) in enumerate(chunk.iterrows()):
                ticker = row.get("ticker","")
                score  = float(row.get("score",0))
                direct = row.get("direction","mixed")
                dur    = row.get("duration","—")
                kelly  = float(row.get("dollar_amount",0) or 0)
                auto   = score >= 70 and alpaca_ok

                if direct == "bullish":
                    acc, ab, abrd, alabel = GREEN, "rgba(0,255,136,0.12)", "rgba(0,255,136,0.35)", "BUY LONG"
                elif direct == "bearish":
                    acc, ab, abrd, alabel = RED,   "rgba(255,45,120,0.12)", "rgba(255,45,120,0.35)", "SELL SHORT"
                else:
                    acc, ab, abrd, alabel = AMBER, "rgba(255,170,0,0.10)",  "rgba(255,170,0,0.30)",  "WATCH"

                if kelly == 0:
                    try:
                        from config import BANKROLL, MAX_POSITION_PCT, KELLY_FRACTION, KELLY_WIN_PCT, KELLY_LOSS_PCT
                        win_p = min(0.75, max(0.35, score / 100 * 0.5 + 0.25))
                        b     = KELLY_WIN_PCT / KELLY_LOSS_PCT
                        f     = max(0, (win_p * b - (1 - win_p)) / b)
                        kelly = round(min(BANKROLL * f * KELLY_FRACTION, BANKROLL * MAX_POSITION_PCT) / 100) * 100
                    except Exception:
                        kelly = 0

                tip    = tooltip_content(row)
                rea    = plain_reason(row)
                ks     = f"${kelly:,.0f}" if kelly else "Calculating..."
                cname  = _cnames.get(ticker, "")

                safe_cname = _html.escape(cname)
                safe_rea   = _html.escape(rea)
                safe_dur   = _html.escape(str(dur))

                cname_html = (
                    '<div style="font-size:10px;color:' + TEXT3 +
                    ';margin-top:1px;margin-bottom:4px;letter-spacing:0.3px;">' +
                    safe_cname + '</div>'
                ) if safe_cname else ''

                auto_html = (
                    "<span class='auto-yes'>&#9889; AUTO-EXECUTING</span>"
                    if auto else
                    "<span class='auto-no'>Manual &middot; score &lt; 70</span>"
                )

                card = "".join([
                    f'<div class="trade-card tt" style="--acc:{acc};--acc2:{acc}33;">',
                    f'<div class="tip">{tip}</div>',
                    '<span class="c c-tl"></span><span class="c c-tr"></span>',
                    '<span class="c c-bl"></span><span class="c c-br"></span>',
                    '<div style="display:flex;justify-content:space-between;'
                    'align-items:flex-start;margin-bottom:10px;"><div>',
                    f'<div class="card-ticker" style="color:{acc};'
                    f'text-shadow:0 0 18px {acc}44;">{ticker}</div>',
                    cname_html,
                    f'<div class="card-action" style="background:{ab};'
                    f'border:1px solid {abrd};color:{acc};">{alabel}</div>',
                    f'<div style="font-size:10px;color:{TEXT2};'
                    f'margin-top:4px;">{safe_dur}</div>',
                    '</div>',
                    ring(score, acc),
                    '</div>',
                    '<div class="card-div"></div>',
                    f'<div class="stars" style="color:{acc};">{stars(score)}</div>',
                    f'<div class="card-reason">{safe_rea}</div>',
                    '<div class="card-footer"><div>',
                    '<div class="card-pos-lbl">Position Size</div>',
                    f'<div class="card-pos" style="color:{acc};">{ks}</div>',
                    '</div>',
                    auto_html,
                    '</div></div>',
                ])
                with cols[ci]:
                    st.markdown(card, unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Scrollable container — 3 rows visible (~880px), scroll inside for the rest
    with st.container(height=880, border=False):
        _render_chunk_rows(sorted_df)
else:
    _is_weekend = datetime.today().weekday() >= 5
    _wait_msg   = ("Markets are closed on weekends — showing last available trading day data." if _is_weekend
                   else "The AI agent runs automatically every weekday at <strong style='color:{GLOW};'>12× daily starting 7:00 AM ET</strong>.<br>Hit <strong style='color:{TEXT};'>⟳ Refresh Dashboard</strong> to check for new results.")
    st.markdown(f"""
    <div class="waiting">
      <div class="wait-ring"></div>
      <div style="font-size:15px;font-weight:600;color:{TEXT};margin-bottom:6px;">
        {"Weekend — market closed" if _is_weekend else "Waiting for today's scan"}
      </div>
      <div style="font-size:12px;color:{TEXT2};line-height:1.8;">{_wait_msg}</div>
    </div>""", unsafe_allow_html=True)

# (Positions are now inside live_alpaca() fragment above — auto-refreshes every 30s)

# ── CHART ─────────────────────────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec">Price Chart &amp; Bollinger Bands</div>', unsafe_allow_html=True)
    sorted_df = picks_df.sort_values("score", ascending=False)
    sel = st.selectbox("Select ticker to chart", sorted_df["ticker"].tolist(), label_visibility="collapsed")
    if sel:
        try:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_c = get_ohlcv(sel, period="6mo")
            if not df_c.empty:
                _bb = BB(df_c["Close"], window=20, window_dev=2)
                fig = go.Figure()
                try:
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1), showlegend=False, name="BB Upper"))
                    fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                        line=dict(color="rgba(0,212,255,0.2)", width=1),
                        fill="tonexty", fillcolor="rgba(0,212,255,0.04)", showlegend=False, name="BB Lower"))
                except Exception:
                    pass
                row_d  = sorted_df[sorted_df["ticker"]==sel].iloc[0]
                direct = row_d.get("direction","mixed")
                acc2   = GREEN if direct=="bullish" else RED if direct=="bearish" else AMBER
                fig.add_trace(go.Candlestick(
                    x=df_c.index, open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"], close=df_c["Close"], name=sel,
                    increasing=dict(line=dict(color=GREEN, width=1.2), fillcolor="rgba(0,255,136,0.2)"),
                    decreasing=dict(line=dict(color=RED,   width=1.2), fillcolor="rgba(255,45,120,0.2)")))
                fig.update_layout(
                    xaxis_rangeslider_visible=False, height=360,
                    paper_bgcolor=SURF, plot_bgcolor=SURF,
                    xaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10)),
                    yaxis=dict(gridcolor="rgba(0,180,255,0.06)", tickfont=dict(color=TEXT2, size=10), side="right"),
                    margin=dict(l=0, r=52, t=28, b=0),
                    title=dict(
                        text=f"<b style='color:{acc2}'>{sel}</b>"
                             f"<span style='color:{TEXT2};font-size:12px;'>  ·  6-Month  ·  Bollinger Bands  ·  Score {float(row_d.get('score',0)):.0f}/100</span>",
                        font=dict(color=TEXT, size=13), x=0.01))
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.markdown(f'<div style="color:{TEXT2};padding:20px;text-align:center;font-size:12px;">Chart unavailable: {e}</div>', unsafe_allow_html=True)

# ── TRADE HISTORY ──────────────────────────────────────────────────────────────
# Closed trade history — pull directly from Alpaca (catches ALL closes, not just DB entries)
_alpaca_closed = []
try:
    if alpaca_ok:
        from execution.alpaca import get_closed_trade_pnl
        _alpaca_closed = get_closed_trade_pnl(days=90)
except Exception:
    pass

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<div class="sec">Closed Trade History <span class="sec-n">{len(_alpaca_closed)} records</span></div>',
    unsafe_allow_html=True)

if not _alpaca_closed:
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.08);border-radius:8px;'
        f'padding:28px;text-align:center;">'
        f'<div style="color:{TEXT2};font-size:13px;font-weight:600;margin-bottom:6px;">No closed trades yet</div>'
        f'<div style="color:{TEXT3};font-size:12px;">Positions appear here after hitting take profit (+7%) or stop loss (-3%)</div>'
        f'</div>',
        unsafe_allow_html=True)
else:
    # Summary totals bar
    _total_won  = sum(t["realized_pnl"] for t in _alpaca_closed if t["realized_pnl"] >= 0)
    _total_lost = sum(t["realized_pnl"] for t in _alpaca_closed if t["realized_pnl"] < 0)
    _net        = _total_won + _total_lost
    _wins       = sum(1 for t in _alpaca_closed if t["realized_pnl"] >= 0)
    _losses     = len(_alpaca_closed) - _wins
    _net_c      = GREEN if _net >= 0 else RED
    _net_sign   = "+" if _net >= 0 else "-"

    # Long / Short win rates
    _longs      = [t for t in _alpaca_closed if t.get("side", "long") == "long"]
    _shorts     = [t for t in _alpaca_closed if t.get("side") == "short"]
    _l_wins     = sum(1 for t in _longs  if t["realized_pnl"] >= 0)
    _s_wins     = sum(1 for t in _shorts if t["realized_pnl"] >= 0)
    _l_wr       = f'{_l_wins/len(_longs)*100:.0f}%'  if _longs  else "—"
    _s_wr       = f'{_s_wins/len(_shorts)*100:.0f}%' if _shorts else "—"
    _l_label    = f'{_l_wr} <span style="font-size:9px;opacity:0.6;">({_l_wins}/{len(_longs)})</span>'
    _s_label    = f'{_s_wr} <span style="font-size:9px;opacity:0.6;">({_s_wins}/{len(_shorts)})</span>'

    st.markdown(
        f'<div style="display:flex;gap:24px;align-items:center;padding:10px 16px;'
        f'background:rgba(0,180,255,0.04);border:1px solid rgba(0,180,255,0.1);'
        f'border-radius:8px;margin-bottom:6px;flex-wrap:wrap;">'
        f'<div><span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Net P&L</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:18px;font-weight:700;'
        f'color:{_net_c};">{_net_sign}${abs(_net):,.2f}</span></div>'
        f'<div><span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Winners</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
        f'color:{GREEN};">+${_total_won:,.2f} <span style="font-size:11px;">({_wins})</span></span></div>'
        f'<div><span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Losers</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
        f'color:{RED};">-${abs(_total_lost):,.2f} <span style="font-size:11px;">({_losses})</span></span></div>'
        f'<div><span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Win Rate</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
        f'color:{AMBER};">{_wins/len(_alpaca_closed)*100:.0f}%</span></div>'
        f'<div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:20px;">'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Long W/R</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
        f'color:{GREEN};">{_l_label}</span></div>'
        f'<div><span style="font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT3};">Short W/R</span><br>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:15px;font-weight:700;'
        f'color:{RED};">{_s_label}</span></div>'
        f'</div>',
        unsafe_allow_html=True)

    # Scrollable table — fixed height with sidebar scrollbar
    _grid = "90px 70px 90px 90px 1fr 90px"
    hdr_html = (
        f'<div class="hist-hdr" style="grid-template-columns:{_grid};position:sticky;top:0;'
        f'background:{SURF};z-index:1;padding:8px 16px;">'
        f'<span class="hist-lbl">Date / Time</span>'
        f'<span class="hist-lbl">Ticker</span>'
        f'<span class="hist-lbl">Entry</span>'
        f'<span class="hist-lbl">Exit</span>'
        f'<span class="hist-lbl">Realized P&L</span>'
        f'<span class="hist-lbl">Outcome</span>'
        f'</div>'
    )
    rows_html = ""
    for cp in _alpaca_closed:
        ticker_  = cp["ticker"]
        rpl      = cp["realized_pnl"]
        rpct     = cp["realized_pnl_pct"]
        entry_p  = cp["entry_price"]
        exit_p   = cp["exit_price"]
        ts       = cp["closed_at"]          # "2026-05-22 14:40"
        ts_date  = ts[:10] if len(ts) >= 10 else ts
        ts_time  = ts[11:16] if len(ts) >= 16 else ""
        outcome  = cp.get("outcome", "manual")
        pc       = GREEN if rpl >= 0 else RED
        arr      = "▲" if rpl >= 0 else "▼"
        bg       = "rgba(0,255,136,0.04)" if rpl >= 0 else "rgba(255,45,120,0.04)"

        pnl_html = (
            f'<span style="color:{pc};font-family:JetBrains Mono,monospace;'
            f'font-weight:700;font-size:14px;">{arr} ${abs(rpl):,.2f}</span>'
            f'<span style="color:{pc};font-size:12px;margin-left:5px;opacity:0.8;">({rpct:+.1f}%)</span>'
        )
        olabel = "🎯 TP" if outcome == "tp_hit" else "🛑 SL" if outcome == "sl_hit" else "✋"
        oc     = GREEN if outcome == "tp_hit" else RED if outcome == "sl_hit" else AMBER

        rows_html += (
            f'<div class="hist-row" style="grid-template-columns:{_grid};'
            f'background:{bg};padding:10px 16px;align-items:center;">'
            f'<span>'
            f'<div style="font-size:11px;color:{TEXT3};font-family:JetBrains Mono,monospace;">{ts_date}</div>'
            f'<div style="font-size:14px;font-weight:700;color:{TEXT};font-family:JetBrains Mono,monospace;">{ts_time}</div>'
            f'</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:16px;font-weight:700;color:{GLOW};">{ticker_}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:{TEXT2};">${entry_p:.2f}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:{TEXT};">${exit_p:.2f}</span>'
            f'<span>{pnl_html}</span>'
            f'<span style="color:{oc};font-size:13px;font-weight:700;">{olabel}</span>'
            f'</div>'
        )

    # Fixed height — shows ~6 rows, scrollable for the rest
    st.markdown(
        f'<div style="background:{SURF};border:1px solid rgba(0,180,255,0.1);'
        f'border-radius:8px;overflow:hidden;">'
        f'{hdr_html}'
        f'<div style="height:330px;overflow-y:scroll;'
        f'scrollbar-width:thin;scrollbar-color:rgba(0,180,255,0.3) transparent;">'
        f'{rows_html}</div>'
        f'</div>',
        unsafe_allow_html=True)

# ── MONTHLY GOAL BAR (bottom of page — live fragment, refreshes every 30s) ─────
@st.fragment(run_every=30)
def live_goal_bar():
    from calendar import monthrange
    from config import MONTHLY_TARGET_PCT, BANKROLL

    today_g        = datetime.today()
    days_in_month  = monthrange(today_g.year, today_g.month)[1]
    day_of_month   = today_g.day
    days_left      = days_in_month - day_of_month
    trading_days   = 21
    trading_day    = round(day_of_month / days_in_month * trading_days)
    # 10% of current account value — not the fixed starting bankroll
    portfolio_val  = st.session_state.get("_portfolio_value", BANKROLL)
    target_dollars = portfolio_val * MONTHLY_TARGET_PCT

    # Monthly realized P&L — sum closed trades for current month from Alpaca history
    _current_month = today_g.strftime("%Y-%m")
    realized_pl = sum(
        cp["realized_pnl"]
        for cp in _alpaca_closed
        if str(cp.get("closed_at", "")).startswith(_current_month)
    )

    # Unrealized — live from fragment (updates every 30s)
    unrealized_pl = st.session_state.get("_live_pl", 0.0)
    total_pl_goal = realized_pl + unrealized_pl

    realized_pct   = max(0, min(100, realized_pl   / target_dollars * 100)) if target_dollars else 0
    unrealized_pct = max(0, min(100 - realized_pct, unrealized_pl / target_dollars * 100)) if target_dollars else 0
    total_pct      = realized_pct + unrealized_pct

    on_pace    = target_dollars * (trading_day / trading_days)
    pace_diff  = total_pl_goal - on_pace
    pace_color = GREEN if pace_diff >= 0 else AMBER if pace_diff > -target_dollars * 0.05 else RED
    pace_lbl   = f"{'▲' if pace_diff >= 0 else '▼'} ${abs(pace_diff):,.0f} {'ahead' if pace_diff >= 0 else 'behind'} pace"

    rl_sign  = "+" if realized_pl   >= 0 else "-"
    sep_sign = "+" if unrealized_pl >= 0 else "−"  # separator changes when unrealized is negative
    # Round before display so components always add up to total
    _rl_display  = round(realized_pl)
    _ul_display  = round(unrealized_pl)
    _tot_display = _rl_display + _ul_display

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(0,255,136,0.04),rgba(0,180,255,0.03));
     border:1px solid rgba(0,255,136,0.15);border-radius:10px;padding:18px 22px;">

  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">
    <div>
      <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEXT2};margin-bottom:8px;">
        Monthly Goal — {today_g.strftime('%B %Y')} &nbsp;·&nbsp; ${target_dollars:,.0f} target (10%)
      </div>
      <div style="display:flex;align-items:center;gap:24px;">
        <div>
          <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
               color:{GREEN};margin-bottom:3px;">🔒 Realized (Closed)</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{GREEN if _rl_display >= 0 else RED};">
            {rl_sign}${abs(_rl_display):,}
          </div>
        </div>
        <div style="color:{TEXT3};font-size:20px;">{sep_sign}</div>
        <div>
          <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
               color:{GLOW if _ul_display >= 0 else RED};margin-bottom:3px;">📈 Unrealized (Open)</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{GLOW if _ul_display >= 0 else RED};">
            ${abs(_ul_display):,}
          </div>
        </div>
        <div style="color:{TEXT3};font-size:20px;">=</div>
        <div>
          <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
               color:{TEXT2};margin-bottom:3px;">Total</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;
               color:{'#00ff88' if _tot_display > 0 else '#ff2d78' if _tot_display < 0 else TEXT2};">
            {"+" if _tot_display >= 0 else "-"}${abs(_tot_display):,}
          </div>
        </div>
      </div>
    </div>
    <div style="text-align:right;display:flex;gap:28px;align-items:flex-start;margin-top:4px;">
      <div>
        <div style="font-size:10px;color:{TEXT3};font-weight:600;letter-spacing:1px;text-transform:uppercase;">Pace</div>
        <div style="font-size:13px;font-weight:700;color:{pace_color};margin-top:3px;">{pace_lbl}</div>
      </div>
      <div>
        <div style="font-size:10px;color:{TEXT3};font-weight:600;letter-spacing:1px;text-transform:uppercase;">Days Left</div>
        <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:3px;">{days_left} days</div>
      </div>
      <div>
        <div style="font-size:10px;color:{TEXT3};font-weight:600;letter-spacing:1px;text-transform:uppercase;">Still Need</div>
        <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:3px;">${max(0, target_dollars - total_pl_goal):,.0f}</div>
      </div>
    </div>
  </div>

  <!-- Two-segment progress bar -->
  <div style="height:10px;background:rgba(0,180,255,0.08);border-radius:5px;overflow:hidden;display:flex;">
    <div style="height:10px;width:{realized_pct:.2f}%;background:{GREEN};
         box-shadow:0 0 10px {GREEN}88;flex-shrink:0;"></div>
    <div style="height:10px;width:{unrealized_pct:.2f}%;background:rgba(0,212,255,0.5);
         flex-shrink:0;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:6px;align-items:center;">
    <span style="font-size:11px;color:{TEXT3};">$0</span>
    <div style="display:flex;gap:16px;align-items:center;">
      <span style="font-size:10px;color:{GREEN};">■ Realized</span>
      <span style="font-size:10px;color:{GLOW};">■ Unrealized</span>
      <span style="font-size:12px;font-weight:700;color:{TEXT2};">{total_pct:.1f}% complete</span>
    </div>
    <span style="font-size:11px;color:{TEXT3};">${target_dollars:,.0f}</span>
  </div>
</div>
""", unsafe_allow_html=True)

live_goal_bar()

# ── Footer — quick links ───────────────────────────────────────────────────────
DASHBOARD_URL = "https://ab2vk4qoxmhxtp5lze8hfl.streamlit.app"
st.markdown(f"""
<div style="margin-top:32px;padding:14px 20px;
     border-top:1px solid rgba(0,180,255,0.08);
     display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
  <div style="display:flex;gap:20px;align-items:center;">
    <span style="font-size:10px;font-weight:700;letter-spacing:1.5px;
                 text-transform:uppercase;color:{TEXT3};">🔺 Illuminati</span>
    <a href="{DASHBOARD_URL}" target="_blank"
       style="font-size:11px;color:{GLOW};text-decoration:none;
              font-family:'JetBrains Mono',monospace;"
       onmouseover="this.style.textDecoration='underline'"
       onmouseout="this.style.textDecoration='none'">
      📊 Scanner
    </a>
    <a href="{DASHBOARD_URL}/Track_Record" target="_blank"
       style="font-size:11px;color:{TEXT2};text-decoration:none;"
       onmouseover="this.style.textDecoration='underline'"
       onmouseout="this.style.textDecoration='none'">
      📈 Track Record
    </a>
    <a href="{DASHBOARD_URL}/Positions" target="_blank"
       style="font-size:11px;color:{TEXT2};text-decoration:none;"
       onmouseover="this.style.textDecoration='underline'"
       onmouseout="this.style.textDecoration='none'">
      💼 Positions
    </a>
    <a href="{DASHBOARD_URL}/Ticker_Dive" target="_blank"
       style="font-size:11px;color:{TEXT2};text-decoration:none;"
       onmouseover="this.style.textDecoration='underline'"
       onmouseout="this.style.textDecoration='none'">
      🔍 Ticker Dive
    </a>
  </div>
  <a href="{DASHBOARD_URL}" target="_blank"
     style="font-size:10px;color:{TEXT3};text-decoration:none;
            font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;"
     onmouseover="this.style.color='{GLOW}'"
     onmouseout="this.style.color='{TEXT3}'">
    {DASHBOARD_URL.replace("https://","")}
  </a>
</div>
""", unsafe_allow_html=True)

# ── Smart tooltip positioning ──────────────────────────────────────────────────
st.markdown("""
<script>
document.querySelectorAll('.tt').forEach(el => {
    el.addEventListener('mouseenter', function(e) {
        const tip = this.querySelector('.tip');
        if (!tip) return;
        const r = this.getBoundingClientRect();
        const tw = 260, th = 200;
        let left = r.left + r.width / 2 - tw / 2;
        let top  = r.bottom + 8;
        if (left < 8) left = 8;
        if (left + tw > window.innerWidth - 8) left = window.innerWidth - tw - 8;
        if (top + th > window.innerHeight - 8) top = r.top - th - 8;
        tip.style.left = left + 'px';
        tip.style.top  = top  + 'px';
    });
});
</script>
""", unsafe_allow_html=True)
