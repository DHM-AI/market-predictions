import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as sp
from ta.volatility import BollingerBands as TaBB, AverageTrueRange as TaATR
from ta.momentum import RSIIndicator as TaRSI
from signals.technicals import _bollinger_pandas, _atr_pandas, _rsi_pandas
from ui_style import inject_css, section_header, score_pill, direction_badge, live_badge, CARD, BORDER, TEXT, MUTED, ACCENT, ACCENT_L, GREEN, RED, AMBER

st.set_page_config(page_title="Ticker Deep Dive", page_icon="📊", layout="wide")
inject_css()

st.markdown(
    f'<h2 style="color:#fafafa;font-weight:700;font-size:22px;">Ticker Deep Dive {live_badge()}</h2>'
    f'<p style="color:#71717a;font-size:13px;margin-top:4px;">Full signal breakdown + AI analysis for any symbol</p>',
    unsafe_allow_html=True
)

col_in, col_btn = st.columns([3, 1])
with col_in:
    ticker_input = st.text_input("", placeholder="Enter symbol — AAPL, TSLA, ES=F, NQ=F ...",
                                  label_visibility="collapsed")
with col_btn:
    analyze = st.button("Analyze", type="primary", use_container_width=True)

if not ticker_input or not analyze:
    st.markdown(
        '<div style="text-align:center;padding:80px 0;font-size:13px;color:#52525b;">'
        '📊 Enter a ticker above and click Analyze</div>',
        unsafe_allow_html=True
    )
    st.stop()

ticker = ticker_input.upper().strip()

with st.spinner(f"Analyzing {ticker}..."):
    from data.fetcher import get_ohlcv, get_earnings_days
    from signals.technicals import compute_all
    from signals.sentiment import get_sentiment_with_velocity
    from signals.scorer import score_ticker

    df = get_ohlcv(ticker, period="1y")
    if df.empty:
        st.error(f"No data found for {ticker}")
        st.stop()

    sentiment  = get_sentiment_with_velocity(ticker)
    earnings   = get_earnings_days(ticker)
    technicals = compute_all(df)
    result     = score_ticker(ticker, df, sentiment, earnings)

# ── Score header ───────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)
score = result.get("score", 0)
sc_color = GREEN if score >= 70 else AMBER if score >= 50 else MUTED
c1.markdown(
    f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:18px;text-align:center;">'
    f'<div style="color:{MUTED};font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:500;">Score</div>'
    f'<div style="font-family:JetBrains Mono,monospace;font-size:38px;font-weight:700;color:{sc_color};margin:4px 0;">{score}</div>'
    f'<div style="color:{MUTED};font-size:11px;">/ 100</div></div>', unsafe_allow_html=True)
c2.markdown(
    f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:18px;text-align:center;">'
    f'<div style="color:{MUTED};font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:500;">Direction</div>'
    f'<div style="font-size:18px;font-weight:700;margin-top:12px;">{direction_badge(result.get("direction","mixed"))}</div>'
    f'</div>', unsafe_allow_html=True)
c3.markdown(
    f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:18px;text-align:center;">'
    f'<div style="color:{MUTED};font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:500;">Window</div>'
    f'<div style="color:{TEXT};font-size:16px;font-weight:600;margin-top:12px;">{result.get("duration","—")}</div>'
    f'</div>', unsafe_allow_html=True)
conf = result.get("confidence", "—")
conf_color = {"High": GREEN, "Medium": AMBER, "Low": MUTED}.get(conf, MUTED)
c4.markdown(
    f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:18px;text-align:center;">'
    f'<div style="color:{MUTED};font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:500;">Confidence</div>'
    f'<div style="color:{conf_color};font-size:18px;font-weight:700;margin-top:12px;">● {conf}</div>'
    f'</div>', unsafe_allow_html=True)

# Signal tags
sigs = result.get("signals_triggered", [])
if sigs:
    st.markdown('<div style="margin:12px 0;">' +
        "".join(f'<span style="display:inline-block;background:#161616;border:1px solid #00ff88;color:#00ff88;'
                f'font-size:11px;padding:3px 10px;border-radius:3px;margin:3px;">{s}</span>' for s in sigs) +
        '</div>', unsafe_allow_html=True)

# ── Signal breakdown ───────────────────────────────────────────────────────────
st.divider()
section_header("SIGNAL BREAKDOWN")

signals_data = [
    ("BB Squeeze",     technicals["bb"]["triggered"],  f"Width pct: {technicals['bb']['width_percentile']}"),
    ("ATR Compression",technicals["atr"]["triggered"], f"Ratio: {technicals['atr']['ratio']}"),
    ("Volume Surge",   technicals["vol"]["triggered"],  f"{technicals['vol']['ratio']}x avg"),
    ("RSI Extreme",    technicals["rsi"]["extreme"],    f"RSI {technicals['rsi']['value']} ({technicals['rsi']['side']})"),
    ("Sentiment Spike",sentiment.get("spike", False),  f"Score {sentiment.get('score',0):.3f} Δ{sentiment.get('velocity',0):.3f}"),
]
if earnings is not None:
    from config import EARNINGS_PROXIMITY_DAYS
    signals_data.append(("Earnings Proximity", 0 <= earnings <= EARNINGS_PROXIMITY_DAYS, f"{earnings}d away"))

cols = st.columns(len(signals_data))
for i, (name, triggered, detail) in enumerate(signals_data):
    color  = GREEN if triggered else MUTED
    border = GREEN if triggered else "#3f3f46"
    icon   = "✓" if triggered else "○"
    pts    = result["breakdown"].get(name.lower().replace(" ","_"), 0)
    cols[i].markdown(
        f'<div style="background:{CARD};border:1px solid {BORDER};border-left:3px solid {border};'
        f'border-radius:10px;padding:14px;text-align:center;">'
        f'<div style="color:{color};font-size:16px;font-weight:700;">{icon}</div>'
        f'<div style="color:{TEXT};font-size:12px;font-weight:600;margin:6px 0 4px;">{name}</div>'
        f'<div style="color:{MUTED};font-size:11px;">{detail}</div>'
        f'<div style="color:{color};font-size:11px;margin-top:6px;font-weight:600;">+{pts} pts</div>'
        f'</div>', unsafe_allow_html=True
    )

# ── Chart ──────────────────────────────────────────────────────────────────────
st.divider()
section_header("CHARTS")

try:
    rsi_s = TaRSI(df["Close"], window=14).rsi()
    atr_s = TaATR(df["High"], df["Low"], df["Close"], window=14).average_true_range()
    _bb   = TaBB(df["Close"], window=20, window_dev=2)
    bb_upper = _bb.bollinger_hband()
    bb_lower = _bb.bollinger_lband()
except Exception:
    rsi_s = _rsi_pandas(df["Close"])
    atr_s = _atr_pandas(df["High"], df["Low"], df["Close"])
    _, _, _, _ = _bollinger_pandas(df["Close"])
    bb_upper = bb_lower = None

fig = sp.make_subplots(rows=3, cols=1, shared_xaxes=True,
                       row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.03)

fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name=ticker,
    increasing=dict(line=dict(color=GREEN), fillcolor="rgba(34,197,94,0.15)"),
    decreasing=dict(line=dict(color=RED),   fillcolor="rgba(239,68,68,0.15)")), row=1, col=1)

if bb_upper is not None and bb_lower is not None:
    fig.add_trace(go.Scatter(x=df.index, y=bb_upper,
        line=dict(color="rgba(99,102,241,0.4)", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_lower,
        line=dict(color="rgba(99,102,241,0.4)", width=1),
        fill="tonexty", fillcolor="rgba(99,102,241,0.04)", showlegend=False), row=1, col=1)

if rsi_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=rsi_s,
        line=dict(color=ACCENT_L, width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=72, line_dash="dot", line_color=RED, row=2, col=1)
    fig.add_hline(y=28, line_dash="dot", line_color=GREEN, row=2, col=1)

if atr_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=atr_s,
        line=dict(color=AMBER, width=1.5),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.06)", name="ATR"), row=3, col=1)

fig.update_layout(height=600, template="plotly_dark",
                  paper_bgcolor=CARD, plot_bgcolor=CARD,
                  xaxis_rangeslider_visible=False,
                  xaxis3=dict(gridcolor=BORDER),
                  yaxis=dict(gridcolor=BORDER),
                  yaxis2=dict(gridcolor=BORDER),
                  yaxis3=dict(gridcolor=BORDER),
                  margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.divider()
section_header("AI ANALYSIS")

if st.button("✦  Generate Claude Analysis", type="primary"):
    from analyst.claude_analyst import stream_explanation
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:18px;">',
        unsafe_allow_html=True
    )
    with st.chat_message("assistant"):
        st.write_stream(stream_explanation(result))
    st.markdown('</div>', unsafe_allow_html=True)
