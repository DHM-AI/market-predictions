import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import inject_css, live_badge, signal_tags, score_chip, direction_html

st.set_page_config(page_title="AI Market Scanner", page_icon="📡", layout="wide")
inject_css()

# ── Local style additions ─────────────────────────────────────────────────────
st.markdown("""
<style>
.top-bar {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 20px;
}
.page-title {
    font-size: 22px; font-weight: 700; color: #fafafa;
    display: flex; align-items: center; gap: 10px;
}
.page-sub { font-size: 13px; color: #71717a; margin-top: 3px; }

/* Pipeline card */
.pipe-card {
    background: #18181b; border: 1px solid #27272a;
    border-radius: 10px; overflow: hidden; margin-bottom: 12px;
}
.pipe-card-title {
    font-size: 11px; font-weight: 600; color: #71717a;
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 10px 16px 9px; border-bottom: 1px solid #27272a;
}
.pip-row {
    display: flex; align-items: center;
    padding: 10px 16px; border-bottom: 1px solid #1f1f23;
    gap: 12px;
}
.pip-row:last-child { border-bottom: none; }
.pip-dot-on  {
    width: 8px; height: 8px; border-radius: 50%;
    background: #22c55e; flex-shrink: 0;
    box-shadow: 0 0 6px rgba(34,197,94,0.5);
}
.pip-dot-pend {
    width: 8px; height: 8px; border-radius: 50%;
    background: #3f3f46; border: 1px solid #52525b; flex-shrink: 0;
}
.pip-name { font-size: 13px; color: #e4e4e7; font-weight: 500; min-width: 80px; }
.pip-sub  { font-size: 11px; color: #52525b; flex: 1; }
.pip-bar  {
    width: 70px; height: 3px; background: #27272a;
    border-radius: 2px; flex-shrink: 0;
}
.pip-fill { height: 3px; background: #22c55e; border-radius: 2px; }
.pip-num-on  { font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600; color:#22c55e; min-width:38px; text-align:right; }
.pip-num-off { font-family:'JetBrains Mono',monospace; font-size:13px; color:#3f3f46; min-width:38px; text-align:right; }

/* Agent card */
.agent-card {
    background: #18181b; border: 1px solid #27272a;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;
    display: flex; justify-content: space-between; align-items: center;
}
.agent-name { font-size: 14px; font-weight: 600; color: #fafafa; display:flex; align-items:center; gap:8px; }
.agent-sub  { font-size: 12px; color: #71717a; margin-top: 4px; margin-left: 16px; }
.agent-count { font-family:'JetBrains Mono',monospace; font-size:28px; font-weight:700; }

/* Qualified box */
.qual-box {
    background: rgba(99,102,241,0.06);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 10px; padding: 14px 18px;
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 4px;
}
.qual-label { color: #818cf8; font-size: 12px; font-weight: 500; }
.qual-sub   { color: #71717a; font-size: 11px; margin-top: 2px; }
.qual-num   {
    font-family:'JetBrains Mono',monospace;
    font-size: 30px; font-weight: 700; color: #818cf8;
}

/* Ticker tape */
.tape-card {
    background: #18181b; border: 1px solid #27272a;
    border-radius: 10px; overflow: hidden;
}
.tape-title {
    font-size: 11px; font-weight: 600; color: #71717a;
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 10px 14px 9px; border-bottom: 1px solid #27272a;
}
.tape-row {
    display: flex; align-items: center;
    padding: 8px 14px; border-bottom: 1px solid #1f1f23;
    font-size: 13px;
}
.tape-row:last-child { border-bottom: none; }
.tape-sym   { font-family:'JetBrains Mono',monospace; font-weight:600; color:#e4e4e7; width:62px; }
.tape-px    { font-family:'JetBrains Mono',monospace; color:#71717a; flex:1; text-align:right; padding-right:10px; font-size:12px; }
.tape-up    { font-family:'JetBrains Mono',monospace; color:#22c55e; min-width:52px; text-align:right; font-size:12px; font-weight:500; }
.tape-dn    { font-family:'JetBrains Mono',monospace; color:#ef4444; min-width:52px; text-align:right; font-size:12px; font-weight:500; }

/* Results table */
.results-wrap {
    background: #18181b; border: 1px solid #27272a;
    border-radius: 10px; overflow: hidden;
}
.results-th {
    padding: 10px 14px; text-align: left;
    color: #71717a; font-size: 11px; font-weight: 500;
    letter-spacing: 0.8px; text-transform: uppercase;
    border-bottom: 1px solid #27272a;
}
.results-tr { border-bottom: 1px solid #1f1f23; }
.results-tr:last-child { border-bottom: none; }
.results-tr:hover td { background: #1f1f23 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("pipeline_counts", {}), ("last_picks", None),
              ("ticker_tape", []), ("scan_time", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([3, 1])
with h_left:
    st.markdown(
        f'<div class="page-title">AI Market Scanner {live_badge()}</div>'
        f'<div class="page-sub">S&P 500 + Futures &nbsp;·&nbsp; 5-Agent Pipeline &nbsp;·&nbsp; 5–10% Move Detection</div>',
        unsafe_allow_html=True
    )
with h_right:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

st.divider()

left_col, right_col = st.columns([1, 2], gap="large")

# ── LEFT: Ticker tape ─────────────────────────────────────────────────────────
with left_col:
    tape_ph = st.empty()

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                '<div class="tape-card">'
                '<div class="tape-title">Market Universe</div>'
                '<div style="padding:48px 16px;text-align:center;">'
                f'<div style="font-size:28px;margin-bottom:10px;">📡</div>'
                f'<div style="color:#52525b;font-size:13px;">Press <strong style="color:#818cf8;">▶ Run Scan</strong><br>to load S&P 500 + Futures</div>'
                '</div></div>',
                unsafe_allow_html=True
            )
            return
        rows = ""
        for t in data[:45]:
            chg = t.get("chg_pct", 0)
            cls = "tape-up" if chg >= 0 else "tape-dn"
            sign = "+" if chg >= 0 else ""
            px = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (
                f'<div class="tape-row">'
                f'<span class="tape-sym">{t["ticker"]}</span>'
                f'<span class="tape-px">{px}</span>'
                f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                f'</div>'
            )
        tape_ph.markdown(
            f'<div class="tape-card"><div class="tape-title">Market Universe — {len(data)} symbols</div>'
            f'<div style="overflow-y:auto;max-height:560px;">{rows}</div></div>',
            unsafe_allow_html=True
        )

    render_tape(st.session_state["ticker_tape"])

# ── RIGHT: Agent + Pipeline + Qualified ───────────────────────────────────────
with right_col:
    agent_ph    = st.empty()
    pipeline_ph = st.empty()
    qual_ph     = st.empty()

    def render_agent(name, sub, count, running=False, done=False):
        dot_color = "#818cf8" if running else ("#22c55e" if done else "#3f3f46")
        val_color = "#818cf8" if running else ("#22c55e" if done else "#52525b")
        pulse = "animation:pulse 0.9s infinite;" if running else ""
        agent_ph.markdown(
            f'<div class="agent-card">'
            f'<div>'
            f'<div class="agent-name">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{dot_color};{pulse}"></span>{name}</div>'
            f'<div class="agent-sub">{sub}</div>'
            f'</div>'
            f'<div class="agent-count" style="color:{val_color};">{count}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    def render_pipeline(counts, universe=509):
        steps = [
            ("Scan",     "Fetch OHLCV · yfinance",             counts.get("universe")),
            ("Research", "Reddit · RSS · Alpha Vantage",        counts.get("research")),
            ("Predict",  "XGBoost + blended sentiment",         counts.get("scored")),
            ("Risk",     "Kelly Criterion · $50k bankroll",      counts.get("risk")),
            ("Learn",    "Backfill actuals · post-mortem",       counts.get("learn")),
        ]
        rows = ""
        for name, sub, cnt in steps:
            done = cnt is not None
            dot  = "pip-dot-on" if done else "pip-dot-pend"
            num_cls = "pip-num-on" if done else "pip-num-off"
            cnt_str = str(cnt) if cnt is not None else "—"
            bar_pct = int((cnt / universe) * 100) if (done and universe) else 0
            rows += (
                f'<div class="pip-row">'
                f'<div class="{dot}"></div>'
                f'<div class="pip-name">{name}</div>'
                f'<div class="pip-sub">{sub}</div>'
                f'<div class="pip-bar"><div class="pip-fill" style="width:{bar_pct}%;"></div></div>'
                f'<div class="{num_cls}">{cnt_str}</div>'
                f'</div>'
            )
        pipeline_ph.markdown(
            f'<div class="pipe-card">'
            f'<div class="pipe-card-title">Filter Pipeline</div>'
            f'{rows}</div>',
            unsafe_allow_html=True
        )

    def render_qualified(n):
        if n > 0:
            qual_ph.markdown(
                f'<div class="qual-box">'
                f'<div><div class="qual-label">Qualified Setups Found</div>'
                f'<div class="qual-sub">Score ≥ 50 · Expected move 5%+</div></div>'
                f'<div class="qual-num">{n}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            qual_ph.markdown(
                f'<div style="background:#18181b;border:1px solid #27272a;border-radius:10px;'
                f'padding:14px 18px;display:flex;justify-content:space-between;align-items:center;">'
                f'<div style="color:#52525b;font-size:13px;">Qualified Setups</div>'
                f'<div style="color:#3f3f46;font-family:JetBrains Mono,monospace;font-size:22px;">—</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    picks_df   = st.session_state["last_picks"]
    counts     = st.session_state["pipeline_counts"]
    scan_time  = st.session_state["scan_time"]
    n_picks    = len(picks_df) if picks_df is not None and not picks_df.empty else 0
    is_done    = scan_time != ""

    render_agent(
        "Market Scan Agent",
        f"Completed at {scan_time}" if scan_time else "Ready — press ▶ Run Scan to start",
        str(n_picks) if n_picks else "—",
        done=is_done
    )
    render_pipeline(counts)
    render_qualified(n_picks)

# ── Run scan logic ────────────────────────────────────────────────────────────
if run_clicked:
    from data.universe import get_universe
    from data.fetcher  import get_ohlcv_batch, get_earnings_days
    from data.research import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly     import annotate_picks
    from model.predictor   import predict_universe
    import db

    tickers = get_universe()
    N = len(tickers)

    render_agent("Market Scan Agent", f"Fetching data for {N} tickers…", str(N), running=True)
    render_pipeline({})
    render_qualified(0)

    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    tape = [
        {"ticker": t, "price": float(df["Close"].iloc[-1]),
         "chg_pct": (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2])) /
                    float(df["Close"].iloc[-2]) * 100}
        for t, df in ohlcv_map.items() if not df.empty and len(df) >= 2
    ]
    tape.sort(key=lambda x: abs(x["chg_pct"]), reverse=True)
    st.session_state["ticker_tape"] = tape
    render_tape(tape)

    render_agent("Research Agent", "Running Reddit · RSS · news sentiment…", str(N), running=True)
    render_pipeline({"universe": N})

    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {
            t: {
                **blended.get(t, {}),
                "score": round(
                    get_sentiment_with_velocity(t).get("score", 0) * 0.4 +
                    blended.get(t, {}).get("score", 0) * 0.6, 4
                ),
                "velocity": get_sentiment_with_velocity(t).get("velocity", 0),
                "spike": (abs(get_sentiment_with_velocity(t).get("velocity", 0)) >= 0.3 or
                          blended.get(t, {}).get("score", 0) > 0.4),
            }
            for t in tickers
        }

    render_agent("Predict Agent", "Scoring with XGBoost + sentiment…", str(N), running=True)
    render_pipeline({"universe": N, "research": N})

    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    render_agent("Risk Agent", "Calculating Kelly Criterion sizes…", str(scored), running=True)
    render_pipeline({"universe": N, "research": N, "scored": scored})

    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    render_agent("Learn Agent", "Persisting to Supabase…", str(scored), running=True)
    render_pipeline({"universe": N, "research": N, "scored": scored, "risk": scored})

    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows = picks_df.copy()
            rows["date"] = datetime.today().strftime("%Y-%m-%d")
            rows["actual_move_5d"] = None
            db.append_predictions(rows.to_dict(orient="records"))

    scan_time = datetime.now().strftime("%H:%M")
    final_counts = {"universe": N, "research": N, "scored": scored, "risk": scored, "learn": scored}
    st.session_state.update({
        "last_picks": picks_df, "scan_time": scan_time,
        "pipeline_counts": final_counts,
    })
    render_agent("Market Scan Agent", f"Completed at {scan_time}", str(scored), done=True)
    render_pipeline(final_counts)
    render_qualified(scored)

# ── Load today's picks from Supabase if no in-session scan ───────────────────
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

# ── Results table ─────────────────────────────────────────────────────────────
if picks_df is not None and not picks_df.empty:
    st.divider()
    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:#fafafa;margin-bottom:12px;">'
        f'{len(picks_df)} setups flagged today</div>',
        unsafe_allow_html=True
    )

    headers = ["Ticker", "Score", "Direction", "Window", "Confidence", "RSI", "Volume", "Kelly $", "Signals"]
    th = "".join(f'<th class="results-th">{h}</th>' for h in headers)

    rows_html = ""
    for _, row in picks_df.iterrows():
        ticker  = row.get("ticker", "")
        score   = row.get("score", 0)
        direct  = row.get("direction", "mixed")
        dur     = row.get("duration", "—")
        conf    = row.get("confidence", "—")
        rsi     = row.get("rsi", "—")
        vol     = row.get("volume_ratio", "—")
        kelly   = row.get("dollar_amount", 0)
        sigs    = row.get("signals_triggered", [])
        if isinstance(sigs, str):
            sigs = [s.strip() for s in sigs.split(";") if s.strip()]

        sc_html  = score_chip(score)
        dir_html = direction_html(direct)
        conf_color = {"High": "#22c55e", "Medium": "#f59e0b", "Low": "#52525b"}.get(conf, "#52525b")
        ks = f'${kelly:,.0f}' if kelly else "—"
        rs = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
        vs = f"{vol:.1f}x" if isinstance(vol, float) else str(vol)
        sh = "".join(
            f'<span style="display:inline-block;background:rgba(99,102,241,0.08);'
            f'border:1px solid rgba(99,102,241,0.25);color:#818cf8;'
            f'font-size:10px;padding:1px 8px;border-radius:20px;margin:1px;">{s}</span>'
            for s in sigs[:3]
        )

        rows_html += (
            f'<tr class="results-tr">'
            f'<td style="padding:11px 14px;font-family:JetBrains Mono,monospace;font-weight:700;color:#fafafa;font-size:14px;">{ticker}</td>'
            f'<td style="padding:11px 14px;">{sc_html}</td>'
            f'<td style="padding:11px 14px;">{dir_html}</td>'
            f'<td style="padding:11px 14px;color:#71717a;font-size:12px;">{dur}</td>'
            f'<td style="padding:11px 14px;color:{conf_color};font-size:12px;font-weight:600;">{conf}</td>'
            f'<td style="padding:11px 14px;font-family:JetBrains Mono,monospace;color:#a1a1aa;font-size:12px;">{rs}</td>'
            f'<td style="padding:11px 14px;font-family:JetBrains Mono,monospace;color:#a1a1aa;font-size:12px;">{vs}</td>'
            f'<td style="padding:11px 14px;font-family:JetBrains Mono,monospace;color:#22c55e;font-weight:600;font-size:13px;">{ks}</td>'
            f'<td style="padding:11px 14px;">{sh}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="results-wrap"><table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
        f'<thead><tr style="background:#1f1f23;">{th}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True
    )

    # ── Mini chart ────────────────────────────────────────────────────────────
    st.divider()
    selected = st.selectbox(
        "Quick chart",
        picks_df["ticker"].tolist(),
        label_visibility="visible"
    )
    if selected:
        from data.fetcher import get_ohlcv
        from ta.volatility import BollingerBands as BB
        df = get_ohlcv(selected, period="6mo")
        if not df.empty:
            _bb = BB(df["Close"], window=20, window_dev=2)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=selected,
                increasing=dict(line=dict(color="#22c55e"), fillcolor="rgba(34,197,94,0.15)"),
                decreasing=dict(line=dict(color="#ef4444"), fillcolor="rgba(239,68,68,0.15)")
            ))
            try:
                fig.add_trace(go.Scatter(x=df.index, y=_bb.bollinger_hband(),
                    line=dict(color="rgba(99,102,241,0.4)", width=1), showlegend=False))
                fig.add_trace(go.Scatter(x=df.index, y=_bb.bollinger_lband(),
                    line=dict(color="rgba(99,102,241,0.4)", width=1),
                    fill="tonexty", fillcolor="rgba(99,102,241,0.04)", showlegend=False))
            except Exception:
                pass
            fig.update_layout(
                xaxis_rangeslider_visible=False, height=340,
                paper_bgcolor="#18181b", plot_bgcolor="#18181b",
                xaxis=dict(gridcolor="#27272a", showgrid=True,
                           tickfont=dict(color="#71717a", size=10)),
                yaxis=dict(gridcolor="#27272a", showgrid=True,
                           tickfont=dict(color="#71717a", size=10)),
                margin=dict(l=0, r=0, t=16, b=0),
                title=dict(text=selected, font=dict(color="#fafafa", size=13), x=0.01)
            )
            st.plotly_chart(fig, use_container_width=True)

            row  = picks_df[picks_df["ticker"] == selected].iloc[0]
            sigs = row.get("signals_triggered", [])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]
            if sigs:
                st.markdown(signal_tags(sigs), unsafe_allow_html=True)
