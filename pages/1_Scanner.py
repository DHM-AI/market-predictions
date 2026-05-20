import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import inject_css, live_badge, section_header, direction_badge, score_pill

st.set_page_config(page_title="AI Market Scanner", page_icon="📡", layout="wide")
inject_css()

# ── Extra layout CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
.pipeline-step {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-bottom: 1px solid #1a1a1a;
    gap: 12px;
}
.pipeline-dot {
    width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.pipeline-dot.active  { background: #00ff88; box-shadow: 0 0 6px #00ff88; }
.pipeline-dot.pending { background: #1e1e1e; border: 1px solid #333; }
.pipeline-dot.warn    { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }

.pipeline-label { color: #e8e8e8; font-size: 13px; flex: 1; }
.pipeline-sub   { color: #444; font-size: 11px; }
.pipeline-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px; font-weight: 700; color: #00ff88; min-width: 48px; text-align: right;
}
.pipeline-count.dim { color: #333; }

.pipeline-bar-wrap { flex: 1; height: 4px; background: #1e1e1e; border-radius: 2px; max-width: 120px; }
.pipeline-bar-fill { height: 4px; background: #00ff88; border-radius: 2px; transition: width 0.4s; }

.qualified-box {
    background: #0a1f0f;
    border: 1px solid #00ff88;
    border-radius: 6px;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 4px;
}
.qualified-label { color: #00ff88; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
.qualified-count { font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 700; color: #00ff88; }

.ticker-list { overflow-y: auto; max-height: 580px; }
.ticker-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 10px;
    border-bottom: 1px solid #151515;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    cursor: pointer;
}
.ticker-item:hover { background: #161616; }
.t-sym   { color: #e8e8e8; font-weight: 600; width: 60px; }
.t-price { color: #888; width: 80px; text-align: right; }
.t-chg   { width: 64px; text-align: right; }
.t-up    { color: #00ff88; }
.t-dn    { color: #ef4444; }

.agent-panel {
    background: #161616;
    border: 1px solid #1e1e1e;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 10px;
}
.agent-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #1e1e1e;
    background: #111;
}
.agent-title  { color: #e8e8e8; font-size: 13px; font-weight: 600; }
.agent-status { color: #00ff88; font-size: 11px; }
.agent-num    { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #00ff88; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════
if "scan_state" not in st.session_state:
    st.session_state["scan_state"] = "idle"   # idle | running | done
if "pipeline_counts" not in st.session_state:
    st.session_state["pipeline_counts"] = {}
if "last_picks" not in st.session_state:
    st.session_state["last_picks"] = None
if "ticker_tape" not in st.session_state:
    st.session_state["ticker_tape"] = []


# ══════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════
header_col, btn_col = st.columns([3, 1])
with header_col:
    st.markdown(
        f'<h2 style="color:#e8e8e8;font-weight:700;margin-bottom:0;">AI Market Scanner{live_badge()}</h2>'
        f'<p style="color:#444;font-size:12px;margin:0;">S&P 500 + Futures · 5-Agent Pipeline · 5-10% Move Detection</p>',
        unsafe_allow_html=True
    )
with btn_col:
    run_clicked = st.button("▶  RUN SCAN", type="primary", use_container_width=True)


st.divider()


# ══════════════════════════════════════════════════════════════════
#  LAYOUT: LEFT ticker tape  |  RIGHT pipeline panel
# ══════════════════════════════════════════════════════════════════
left_col, right_col = st.columns([1, 2], gap="medium")


# ── LEFT: Ticker tape ──────────────────────────────────────────────
with left_col:
    st.markdown('<div style="color:#444;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">Active Universe</div>', unsafe_allow_html=True)

    tape_placeholder = st.empty()

    def render_ticker_tape(tickers_data: list[dict]):
        if not tickers_data:
            tape_placeholder.markdown(
                '<div style="color:#333;padding:40px 0;text-align:center;font-size:12px;">Run a scan to populate</div>',
                unsafe_allow_html=True
            )
            return
        rows = ""
        for t in tickers_data[:40]:
            chg = t.get("chg_pct", 0)
            cls = "t-up" if chg >= 0 else "t-dn"
            arrow = "▲" if chg >= 0 else "▼"
            price_str = f"${t.get('price', 0):,.2f}" if t.get("price") else "—"
            rows += (f'<div class="ticker-item">'
                     f'<span class="t-sym">{t["ticker"]}</span>'
                     f'<span class="t-price">{price_str}</span>'
                     f'<span class="t-chg {cls}">{arrow}{abs(chg):.1f}%</span>'
                     f'</div>')
        tape_placeholder.markdown(
            f'<div class="agent-panel"><div class="ticker-list">{rows}</div></div>',
            unsafe_allow_html=True
        )

    render_ticker_tape(st.session_state["ticker_tape"])


# ── RIGHT: Pipeline panel ──────────────────────────────────────────
with right_col:

    # Agent status card
    agent_placeholder = st.empty()
    pipeline_placeholder = st.empty()
    qualified_placeholder = st.empty()

    def render_agent_card(title: str, subtitle: str, count: str, running: bool = False):
        dot_color = "#00ff88" if running else "#333"
        pulse = "animation:pulse 1s infinite;" if running else ""
        agent_placeholder.markdown(f"""
        <div class="agent-panel">
          <div class="agent-header">
            <div>
              <div class="agent-title">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                  background:{dot_color};margin-right:8px;{pulse}"></span>
                {title}
              </div>
              <div style="color:#444;font-size:11px;margin-top:2px;">{subtitle}</div>
            </div>
            <div class="agent-num">{count}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    def render_pipeline(counts: dict, universe_size: int = 509):
        steps = [
            ("1 · SCAN",        "Fetch OHLCV · yfinance",                   counts.get("universe",    universe_size), universe_size,  True),
            ("2 · RESEARCH",    "Reddit · RSS · Alpha Vantage · yfinance",   counts.get("research",    None),          universe_size,  counts.get("research") is not None),
            ("3 · PREDICT",     "XGBoost + sentiment → probability score",   counts.get("scored",      None),          universe_size,  counts.get("scored") is not None),
            ("4 · RISK",        "Kelly Criterion · $50k bankroll",           counts.get("risk",        None),          universe_size,  counts.get("risk") is not None),
            ("5 · LEARN",       "Backfill actuals · post-mortem loop",       counts.get("learn",       None),          universe_size,  counts.get("learn") is not None),
        ]

        html = '<div class="agent-panel">'
        html += '<div style="padding:10px 14px;background:#111;border-bottom:1px solid #1a1a1a;color:#444;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;">Filter Pipeline</div>'

        for label, sub, count, total, active in steps:
            dot_cls   = "active" if active else "pending"
            count_cls = "" if active else "dim"
            count_str = str(count) if count is not None else "—"
            bar_pct   = int((count / total) * 100) if (count and total) else 0

            html += f"""
            <div class="pipeline-step">
              <div class="pipeline-dot {dot_cls}"></div>
              <div style="flex:1;">
                <div class="pipeline-label">{label}</div>
                <div class="pipeline-sub">{sub}</div>
              </div>
              <div class="pipeline-bar-wrap">
                <div class="pipeline-bar-fill" style="width:{bar_pct}%;"></div>
              </div>
              <div class="pipeline-count {count_cls}">{count_str}</div>
            </div>
            """
        html += "</div>"
        pipeline_placeholder.markdown(html, unsafe_allow_html=True)

    def render_qualified(n: int):
        color = "#00ff88" if n > 0 else "#333"
        border_color = "#00ff88" if n > 0 else "#1e1e1e"
        bg_color = "#0a1f0f" if n > 0 else "#111"
        qualified_placeholder.markdown(f"""
        <div style="background:{bg_color};border:1px solid {border_color};border-radius:6px;
             padding:16px 20px;display:flex;justify-content:space-between;align-items:center;">
          <div style="color:{color};font-size:11px;letter-spacing:2px;text-transform:uppercase;">
            Qualified Setups
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;color:{color};">
            {n} {"FOUND" if n > 0 else "—"}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Initial render
    picks_df = st.session_state.get("last_picks")
    counts   = st.session_state.get("pipeline_counts", {})
    scan_time = st.session_state.get("scan_time", "")

    render_agent_card(
        "Market Scan Agent",
        f"Last scan: {scan_time}" if scan_time else "Ready — click RUN SCAN",
        str(counts.get("universe", "—")),
        running=False
    )
    render_pipeline(counts)
    render_qualified(len(picks_df) if picks_df is not None and not picks_df.empty else 0)


# ══════════════════════════════════════════════════════════════════
#  RUN SCAN (live pipeline updates)
# ══════════════════════════════════════════════════════════════════
if run_clicked:
    import time
    from data.universe import get_universe
    from data.fetcher import get_ohlcv_batch, get_earnings_days
    from data.research import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly import annotate_picks
    from model.predictor import predict_universe, model_available
    from analyst.claude_analyst import explain_picks
    import db

    tickers = get_universe()
    universe_size = len(tickers)

    # ── Stage 1: Scan ──────────────────────────────────────────────
    render_agent_card("1 · Scan Agent", f"Fetching OHLCV for {universe_size} tickers...",
                      str(universe_size), running=True)
    render_pipeline({"universe": universe_size})
    render_qualified(0)

    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    # Build ticker tape from fetched data
    tape = []
    for t, df in list(ohlcv_map.items())[:40]:
        if df.empty or len(df) < 2:
            continue
        price = float(df["Close"].iloc[-1])
        prev  = float(df["Close"].iloc[-2])
        chg   = (price - prev) / prev * 100
        tape.append({"ticker": t, "price": price, "chg_pct": chg})
    tape.sort(key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["ticker_tape"] = tape
    render_ticker_tape(tape)

    # ── Stage 2: Research ──────────────────────────────────────────
    render_agent_card("2 · Research Agent", "Reddit · RSS · Alpha Vantage · yfinance",
                      str(universe_size), running=True)
    render_pipeline({"universe": universe_size, "research": universe_size})

    with st.spinner(""):
        blended_sentiment = research_universe(tickers)
        sentiment_map: dict = {}
        for ticker in tickers:
            cached = get_sentiment_with_velocity(ticker)
            blended = blended_sentiment.get(ticker, {})
            combined = cached.get("score", 0.0) * 0.4 + blended.get("score", 0.0) * 0.6
            sentiment_map[ticker] = {
                **blended, "score": round(combined, 4),
                "velocity": cached.get("velocity", 0.0),
                "spike": abs(cached.get("velocity", 0.0)) >= 0.3 or blended.get("score", 0) > 0.4,
            }

    # ── Stage 3: Predict ───────────────────────────────────────────
    render_agent_card("3 · Predict Agent", "XGBoost + blended sentiment",
                      str(universe_size), running=True)
    render_pipeline({"universe": universe_size, "research": universe_size,
                     "scored": universe_size})

    with st.spinner(""):
        earnings_map: dict = {}
        for t in tickers[:100]:
            earnings_map[t] = get_earnings_days(t)
        picks_df = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored_count = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    # ── Stage 4: Risk ──────────────────────────────────────────────
    render_agent_card("4 · Risk Agent", "Kelly Criterion sizing", str(scored_count), running=True)
    render_pipeline({"universe": universe_size, "research": universe_size,
                     "scored": scored_count, "risk": scored_count})

    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    # ── Stage 5: Learn ─────────────────────────────────────────────
    render_agent_card("5 · Learn Agent", "Backfilling actuals · Persisting predictions",
                      str(scored_count), running=True)
    render_pipeline({"universe": universe_size, "research": universe_size,
                     "scored": scored_count, "risk": scored_count, "learn": scored_count})

    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows = picks_df.copy()
            rows["date"] = datetime.today().strftime("%Y-%m-%d")
            rows["actual_move_5d"] = None
            db.append_predictions(rows.to_dict(orient="records"))

    # ── Final state ─────────────────────────────────────────────────
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state["last_picks"]      = picks_df
    st.session_state["scan_time"]       = scan_time
    st.session_state["pipeline_counts"] = {
        "universe": universe_size, "research": universe_size,
        "scored": scored_count, "risk": scored_count, "learn": scored_count
    }

    render_agent_card("Market Scan Agent", f"Completed · {scan_time}",
                      str(scored_count), running=False)
    render_pipeline(st.session_state["pipeline_counts"])
    render_qualified(scored_count)


# ══════════════════════════════════════════════════════════════════
#  LOAD results from Supabase if no session scan
# ══════════════════════════════════════════════════════════════════
if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
                render_qualified(len(picks_df))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  RESULTS TABLE
# ══════════════════════════════════════════════════════════════════
if picks_df is not None and not picks_df.empty:
    st.divider()
    section_header("QUALIFIED SETUPS")

    rows_html = ""
    for _, row in picks_df.iterrows():
        score   = row.get("score", 0)
        ticker  = row.get("ticker", "")
        direct  = row.get("direction", "mixed")
        dur     = row.get("duration", "—")
        conf    = row.get("confidence", "—")
        rsi     = row.get("rsi", "—")
        vol_r   = row.get("volume_ratio", "—")
        kelly   = row.get("dollar_amount", 0)
        risk_lv = row.get("risk_level", "—")

        conf_color = {"High": "#00ff88", "Medium": "#f59e0b", "Low": "#555"}.get(conf, "#555")
        dir_html   = direction_badge(direct)
        score_html = score_pill(score)
        kelly_str  = f"${kelly:,.0f}" if kelly else "—"
        rsi_str    = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
        vol_str    = f"{vol_r:.1f}x" if isinstance(vol_r, float) else str(vol_r)

        risk_color = {"aggressive": "#ef4444", "moderate": "#f59e0b",
                      "conservative": "#00ff88", "skip": "#333"}.get(risk_lv, "#555")

        rows_html += f"""
        <tr style="border-bottom:1px solid #151515;">
          <td style="padding:11px 14px;font-family:'JetBrains Mono',monospace;
              font-weight:700;color:#e8e8e8;font-size:14px;">{ticker}</td>
          <td style="padding:11px 14px;">{score_html}</td>
          <td style="padding:11px 14px;">{dir_html}</td>
          <td style="padding:11px 14px;color:#555;font-size:12px;">{dur}</td>
          <td style="padding:11px 14px;color:{conf_color};font-size:12px;font-weight:600;">{conf}</td>
          <td style="padding:11px 14px;font-family:'JetBrains Mono',monospace;
              color:#888;font-size:13px;">{rsi_str}</td>
          <td style="padding:11px 14px;font-family:'JetBrains Mono',monospace;
              color:#888;font-size:13px;">{vol_str}</td>
          <td style="padding:11px 14px;font-family:'JetBrains Mono',monospace;
              color:#00ff88;font-weight:700;">{kelly_str}</td>
          <td style="padding:11px 14px;color:{risk_color};font-size:11px;
              font-weight:600;text-transform:uppercase;">{risk_lv}</td>
        </tr>"""

    st.markdown(f"""
    <div style="border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;">
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;background:#0d0d0d;">
      <thead>
        <tr style="background:#111;">
          {"".join(
              f'<th style="padding:10px 14px;text-align:left;color:#333;'
              f'font-size:10px;letter-spacing:1.5px;text-transform:uppercase;">{h}</th>'
              for h in ["Ticker","Score","Direction","Window","Confidence","RSI","Vol Ratio","Kelly Size","Risk"]
          )}
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

    # ── Per-ticker chart ───────────────────────────────────────────────────────
    st.divider()
    section_header("PRICE CHART")

    tickers_list = picks_df["ticker"].tolist()
    selected = st.selectbox("", tickers_list, label_visibility="collapsed")

    if selected:
        from data.fetcher import get_ohlcv
        import pandas_ta as ta

        df = get_ohlcv(selected, period="6mo")
        if not df.empty:
            bbands = ta.bbands(df["Close"], length=20)

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=selected,
                increasing=dict(line=dict(color="#00ff88"), fillcolor="#00ff8822"),
                decreasing=dict(line=dict(color="#ef4444"), fillcolor="#ef444422"),
            ))
            if bbands is not None and not bbands.empty:
                u = [c for c in bbands.columns if "BBU" in c]
                l = [c for c in bbands.columns if "BBL" in c]
                m = [c for c in bbands.columns if "BBM" in c]
                if u and l and m:
                    fig.add_trace(go.Scatter(x=df.index, y=bbands[u[0]],
                        line=dict(color="#1e3a1e", width=1), showlegend=False))
                    fig.add_trace(go.Scatter(x=df.index, y=bbands[l[0]],
                        line=dict(color="#1e3a1e", width=1),
                        fill="tonexty", fillcolor="rgba(0,255,136,0.03)", showlegend=False))

            fig.update_layout(
                xaxis_rangeslider_visible=False, height=380,
                template="plotly_dark",
                paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                xaxis=dict(gridcolor="#111", showgrid=True, zeroline=False),
                yaxis=dict(gridcolor="#111", showgrid=True, zeroline=False),
                margin=dict(l=0, r=0, t=16, b=0),
                title=dict(text=f"{selected}", font=dict(color="#e8e8e8", size=14), x=0.01),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Signal chips
            row = picks_df[picks_df["ticker"] == selected].iloc[0]
            sigs = row.get("signals_triggered", [])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]
            if sigs:
                st.markdown(
                    "".join(f'<span style="display:inline-block;background:#0a1f0f;'
                            f'border:1px solid #00ff88;color:#00ff88;font-size:11px;'
                            f'padding:3px 10px;border-radius:3px;margin:3px;">{s}</span>'
                            for s in sigs),
                    unsafe_allow_html=True
                )
