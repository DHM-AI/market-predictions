import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import (
    inject_css, live_badge, signal_tags, score_chip, direction_html,
    BG, SURF, SURF2, BORDER, BORDER2, TEXT, TEXT2, TEXT3,
    BULL, BEAR, WATCH, BLUE, CYAN, PURPLE,
)

st.set_page_config(page_title="AI Market Scanner", page_icon="⚡", layout="wide")
inject_css()

st.markdown(f"""
<style>
/* ══════════════════════════════════════════════════════
   HEADER
══════════════════════════════════════════════════════ */
.hdr {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-bottom: 18px;
}}
.hdr-left  {{ display: flex; flex-direction: column; gap: 2px; }}
.hdr-title {{ font-size: 17px; font-weight: 700; color: {TEXT}; display: flex; align-items: center; gap: 8px; }}
.hdr-sub   {{ font-size: 12px; color: {TEXT3}; margin-left: 0; }}

/* ══════════════════════════════════════════════════════
   STAT CARDS
══════════════════════════════════════════════════════ */
.stat-card {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
}}
.stat-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent, {TEXT3});
    opacity: 0.6;
}}
.stat-label {{ font-size: 10px; font-weight: 600; color: {TEXT3}; text-transform: uppercase; letter-spacing: 1.2px; }}
.stat-val   {{ font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 700; color: var(--accent, {TEXT}); margin: 4px 0 2px; line-height: 1; }}
.stat-sub   {{ font-size: 11px; color: {TEXT3}; }}

/* ══════════════════════════════════════════════════════
   SECTION HEADER (inline)
══════════════════════════════════════════════════════ */
.sec {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid {BORDER};
}}
.sec-title {{ font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: {TEXT3}; }}
.sec-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 600; color: {TEXT3};
    background: {SURF2}; border: 1px solid {BORDER};
    padding: 1px 9px; border-radius: 20px;
}}

/* ══════════════════════════════════════════════════════
   PICKS TABLE
══════════════════════════════════════════════════════ */
.picks-wrap {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
}}
.picks-thead th {{
    padding: 9px 14px;
    font-size: 10px; font-weight: 600; color: {TEXT3};
    text-transform: uppercase; letter-spacing: 1px;
    text-align: left;
    background: {SURF2};
    border-bottom: 1px solid {BORDER};
    white-space: nowrap;
}}
.picks-tbody tr {{
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.1s;
}}
.picks-tbody tr:last-child {{ border-bottom: none; }}
.picks-tbody tr:hover td {{ background: rgba(255,255,255,0.03); }}
.picks-tbody td {{
    padding: 11px 14px;
    vertical-align: middle;
}}
.sym {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 700; color: {CYAN};
    letter-spacing: -0.3px;
}}
.conf-hi  {{ color: {BULL};  font-size: 12px; font-weight: 600; }}
.conf-med {{ color: {WATCH}; font-size: 12px; font-weight: 600; }}
.conf-lo  {{ color: {TEXT3}; font-size: 12px; font-weight: 600; }}
.mono-sm  {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: {TEXT2}; }}
.kelly    {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: {BULL}; }}

/* ══════════════════════════════════════════════════════
   PIPELINE PANEL
══════════════════════════════════════════════════════ */
.pipe-wrap {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
}}
.pipe-hdr {{
    padding: 9px 14px;
    font-size: 10px; font-weight: 700; color: {TEXT3};
    letter-spacing: 1.5px; text-transform: uppercase;
    background: {SURF2};
    border-bottom: 1px solid {BORDER};
    display: flex; justify-content: space-between; align-items: center;
}}
.pipe-step {{
    display: flex; align-items: center;
    padding: 10px 14px;
    gap: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.pipe-step:last-child {{ border-bottom: none; }}
.p-dot-on  {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {BULL}; flex-shrink: 0;
    box-shadow: 0 0 8px {BULL}88;
}}
.p-dot-off {{
    width: 8px; height: 8px; border-radius: 50%;
    background: transparent; flex-shrink: 0;
    border: 1.5px solid {TEXT3};
}}
.p-dot-run {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {BLUE}; flex-shrink: 0;
    box-shadow: 0 0 8px {BLUE}88;
    animation: livepulse 0.8s infinite;
}}
.p-name {{ font-size: 12px; font-weight: 600; color: {TEXT}; width: 70px; flex-shrink: 0; }}
.p-desc {{ font-size: 11px; color: {TEXT3}; flex: 1; }}
.p-track {{
    width: 54px; height: 3px;
    background: rgba(255,255,255,0.07); border-radius: 2px; flex-shrink: 0;
}}
.p-fill  {{ height: 3px; border-radius: 2px; background: {BULL}; }}
.p-num-on  {{ font-family: JetBrains Mono,monospace; font-size: 12px; font-weight: 700; color: {BULL}; min-width: 32px; text-align: right; }}
.p-num-off {{ font-family: JetBrains Mono,monospace; font-size: 12px; color: {TEXT3}; min-width: 32px; text-align: right; }}

/* ══════════════════════════════════════════════════════
   UNIVERSE TAPE
══════════════════════════════════════════════════════ */
.tape-wrap {{
    background: {SURF};
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    margin-top: 12px;
}}
.tape-hdr {{
    padding: 9px 14px;
    font-size: 10px; font-weight: 700; color: {TEXT3};
    letter-spacing: 1.5px; text-transform: uppercase;
    background: {SURF2};
    border-bottom: 1px solid {BORDER};
    display: flex; justify-content: space-between;
}}
.tape-row {{
    display: flex; align-items: center;
    padding: 7px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}}
.tape-row:last-child {{ border-bottom: none; }}
.tape-row:hover {{ background: rgba(255,255,255,0.02); }}
.t-sym {{ font-family: JetBrains Mono,monospace; font-weight: 700; color: {CYAN}; font-size: 12px; width: 56px; }}
.t-px  {{ font-family: JetBrains Mono,monospace; font-size: 11px; color: {TEXT3}; flex: 1; text-align: right; padding-right: 10px; }}
.t-up  {{ font-family: JetBrains Mono,monospace; font-size: 11px; color: {BULL}; min-width: 46px; text-align: right; font-weight: 600; }}
.t-dn  {{ font-family: JetBrains Mono,monospace; font-size: 11px; color: {BEAR}; min-width: 46px; text-align: right; font-weight: 600; }}

/* ══════════════════════════════════════════════════════
   EMPTY STATE
══════════════════════════════════════════════════════ */
.empty-state {{
    padding: 60px 20px;
    text-align: center;
}}
.empty-icon  {{ font-size: 36px; margin-bottom: 12px; opacity: 0.5; }}
.empty-title {{ font-size: 15px; font-weight: 600; color: {TEXT2}; margin-bottom: 6px; }}
.empty-sub   {{ font-size: 13px; color: {TEXT3}; }}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("pipeline_counts", {}), ("last_picks", None),
              ("ticker_tape", []), ("scan_time", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Load today's picks from DB if available ───────────────────────────────────
picks_df  = st.session_state["last_picks"]
counts    = st.session_state["pipeline_counts"]
scan_time = st.session_state["scan_time"]

if picks_df is None:
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows:
                picks_df = pd.DataFrame(rows)
    except Exception:
        pass

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
n_high  = int((picks_df["score"] >= 70).sum()) if picks_df is not None and not picks_df.empty and "score" in picks_df.columns else 0
n_bull  = int((picks_df["direction"] == "bullish").sum()) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
n_bear  = int((picks_df["direction"] == "bearish").sum()) if picks_df is not None and not picks_df.empty and "direction" in picks_df.columns else 0
univ    = counts.get("universe", 0)

# ── Header ────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([5, 1])
with hc1:
    updated = f"Last scan {scan_time} · {datetime.today().strftime('%b %d, %Y')}" if scan_time else f"No scan yet · {datetime.today().strftime('%b %d, %Y')}"
    st.markdown(
        f'<div class="hdr">'
        f'<div class="hdr-left">'
        f'<div class="hdr-title">⚡ AI Market Scanner {live_badge()}</div>'
        f'<div class="hdr-sub">S&P 500 · Futures · 5-Agent Pipeline · 5–10% Move Detection &nbsp;·&nbsp; {updated}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )
with hc2:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

# ── Stat cards ────────────────────────────────────────────────────────────────
def stat_card(col, label, val, sub, accent):
    col.markdown(
        f'<div class="stat-card" style="--accent:{accent};">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-val">{val}</div>'
        f'<div class="stat-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

c1,c2,c3,c4,c5,c6 = st.columns(6)
stat_card(c1, "Universe",       f"{univ:,}" if univ else "—",          "S&P 500 + Futures",  TEXT3)
stat_card(c2, "Qualified",      str(n_picks) if n_picks else "—",       "Score ≥ 50 · 5%+ move", BULL if n_picks else TEXT3)
stat_card(c3, "High Conviction",str(n_high)  if n_high  else "—",       "Score ≥ 70",         BULL if n_high else TEXT3)
stat_card(c4, "Long Setups",    str(n_bull)  if n_bull  else "—",       "Bullish bias",       BULL if n_bull else TEXT3)
stat_card(c5, "Short Setups",   str(n_bear)  if n_bear  else "—",       "Bearish bias",       BEAR if n_bear else TEXT3)
stat_card(c6, "Last Scan",      scan_time    if scan_time else "—",     "Today",              BLUE if scan_time else TEXT3)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Main layout ───────────────────────────────────────────────────────────────
left, right = st.columns([5, 2], gap="medium")

# ══════════════════════════════════════════════════════
# RIGHT PANEL
# ══════════════════════════════════════════════════════
with right:
    agent_ph    = st.empty()
    pipeline_ph = st.empty()
    tape_ph     = st.empty()

    def render_agent(name, sub, count, state="idle"):
        color = {
            "idle":    TEXT3,
            "running": BLUE,
            "done":    BULL,
        }.get(state, TEXT3)
        pulse = "animation:livepulse 0.8s infinite;" if state == "running" else ""
        agent_ph.markdown(
            f'<div style="background:{SURF};border:1px solid {BORDER};border-radius:10px;'
            f'padding:12px 16px;margin-bottom:12px;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<div style="font-size:13px;font-weight:600;color:{TEXT};'
            f'display:flex;align-items:center;gap:8px;">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{color};'
            f'display:inline-block;{pulse}"></span>{name}</div>'
            f'<div style="font-size:11px;color:{TEXT3};margin-top:3px;margin-left:15px;">{sub}</div>'
            f'</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:22px;'
            f'font-weight:700;color:{color};">{count}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    def render_pipeline(counts, N=509):
        steps = [
            ("Scan",     "OHLCV · yfinance",       counts.get("universe")),
            ("Research", "Reddit · RSS · news",     counts.get("research")),
            ("Predict",  "XGBoost + sentiment",     counts.get("scored")),
            ("Risk",     "Kelly · $50k bankroll",   counts.get("risk")),
            ("Learn",    "Backfill · post-mortem",  counts.get("learn")),
        ]
        rows = ""
        n_done = 0
        for name, desc, cnt in steps:
            done = cnt is not None
            if done: n_done += 1
            dot  = "p-dot-on" if done else "p-dot-off"
            ncls = "p-num-on" if done else "p-num-off"
            cs   = str(cnt) if done else "—"
            bw   = int((cnt / N) * 100) if (done and N) else 0
            rows += (
                f'<div class="pipe-step">'
                f'<div class="{dot}"></div>'
                f'<div class="p-name">{name}</div>'
                f'<div class="p-desc">{desc}</div>'
                f'<div class="p-track"><div class="p-fill" style="width:{bw}%;"></div></div>'
                f'<div class="{ncls}">{cs}</div>'
                f'</div>'
            )
        done_color = BULL if n_done == 5 else (BLUE if n_done > 0 else TEXT3)
        pipeline_ph.markdown(
            f'<div class="pipe-wrap">'
            f'<div class="pipe-hdr"><span>Pipeline</span>'
            f'<span style="font-family:JetBrains Mono,monospace;color:{done_color};">{n_done}/5</span></div>'
            f'{rows}</div>',
            unsafe_allow_html=True
        )

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                f'<div class="tape-wrap">'
                f'<div class="tape-hdr"><span>Universe</span><span>—</span></div>'
                f'<div class="empty-state" style="padding:30px 14px;">'
                f'<div class="empty-icon">📡</div>'
                f'<div class="empty-sub">Run scan to load</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )
            return
        rows = ""
        for t in data[:32]:
            chg  = t.get("chg_pct", 0)
            cls  = "t-up" if chg >= 0 else "t-dn"
            sign = "+" if chg >= 0 else ""
            px   = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (
                f'<div class="tape-row">'
                f'<span class="t-sym">{t["ticker"]}</span>'
                f'<span class="t-px">{px}</span>'
                f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                f'</div>'
            )
        tape_ph.markdown(
            f'<div class="tape-wrap">'
            f'<div class="tape-hdr"><span>Universe</span>'
            f'<span style="font-family:JetBrains Mono,monospace;">{len(data)}</span></div>'
            f'<div style="overflow-y:auto;max-height:300px;">{rows}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    is_done = bool(scan_time)
    render_agent(
        "Scan Agent",
        f"Done at {scan_time}" if is_done else "Ready — press Run Scan",
        str(n_picks) if n_picks else "—",
        state="done" if is_done else "idle"
    )
    render_pipeline(counts)
    render_tape(st.session_state["ticker_tape"])

# ══════════════════════════════════════════════════════
# LEFT PANEL — picks table
# ══════════════════════════════════════════════════════
with left:
    picks_ph = st.empty()

    def render_picks(df):
        if df is None or df.empty:
            picks_ph.markdown(
                f'<div class="picks-wrap">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:9px 14px;background:{SURF2};border-bottom:1px solid {BORDER};">'
                f'<span style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{TEXT3};">Today\'s Setups</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
                f'color:{TEXT3};background:{SURF};border:1px solid {BORDER};'
                f'padding:1px 9px;border-radius:20px;">0</span></div>'
                f'<div class="empty-state">'
                f'<div class="empty-icon">🔍</div>'
                f'<div class="empty-title">No setups found yet</div>'
                f'<div class="empty-sub">Press ▶ Run Scan to analyze S&P 500 + Futures<br>and surface high-conviction opportunities.</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )
            return

        hdrs = ["SYMBOL", "DIRECTION", "SCORE", "CONFIDENCE", "WINDOW", "RSI", "VOLUME", "KELLY $", "SIGNALS"]
        th = "".join(f'<th class="picks-thead th">{h}</th>' for h in hdrs)

        # rebuild thead with correct class
        th_cells = "".join(
            f'<th style="padding:9px 14px;font-size:10px;font-weight:600;color:{TEXT3};'
            f'text-transform:uppercase;letter-spacing:1px;text-align:left;'
            f'background:{SURF2};border-bottom:1px solid {BORDER};white-space:nowrap;">{h}</th>'
            for h in hdrs
        )

        rows_html = ""
        for _, row in df.sort_values("score", ascending=False).iterrows():
            ticker = row.get("ticker", "")
            score  = row.get("score", 0)
            direct = row.get("direction", "mixed")
            dur    = row.get("duration", "—")
            conf   = row.get("confidence", "—")
            rsi    = row.get("rsi", "—")
            vol    = row.get("volume_ratio", "—")
            kelly  = row.get("dollar_amount", 0)
            sigs   = row.get("signals_triggered", [])
            if isinstance(sigs, str):
                sigs = [s.strip() for s in sigs.split(";") if s.strip()]

            # Left border color by direction
            lborder = BULL if direct == "bullish" else (BEAR if direct == "bearish" else WATCH)
            conf_cls = {"High": f"color:{BULL};", "Medium": f"color:{WATCH};", "Low": f"color:{TEXT3};"}.get(conf, f"color:{TEXT3};")
            ks  = f'${kelly:,.0f}' if kelly else "—"
            rs  = f"{rsi:.1f}" if isinstance(rsi, float) else str(rsi)
            vs  = f"{vol:.1f}×" if isinstance(vol, float) else str(vol)
            sh  = " ".join(
                f'<span style="display:inline-block;background:{SURF2};border:1px solid {BORDER};'
                f'color:{TEXT2};font-size:10px;padding:2px 8px;border-radius:4px;">{s}</span>'
                for s in sigs[:3]
            )

            rows_html += (
                f'<tr style="border-left:2px solid {lborder};border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'<td style="padding:12px 14px;"><span class="sym">{ticker}</span></td>'
                f'<td style="padding:12px 14px;">{direction_html(direct)}</td>'
                f'<td style="padding:12px 14px;">{score_chip(score)}</td>'
                f'<td style="padding:12px 14px;font-size:12px;font-weight:600;{conf_cls}">{conf}</td>'
                f'<td style="padding:12px 14px;font-size:12px;color:{TEXT2};">{dur}</td>'
                f'<td style="padding:12px 14px;font-family:JetBrains Mono,monospace;font-size:12px;color:{TEXT2};">{rs}</td>'
                f'<td style="padding:12px 14px;font-family:JetBrains Mono,monospace;font-size:12px;color:{TEXT2};">{vs}</td>'
                f'<td style="padding:12px 14px;font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:{BULL};">{ks}</td>'
                f'<td style="padding:12px 14px;">{sh}</td>'
                f'</tr>'
            )

        picks_ph.markdown(
            f'<div class="picks-wrap">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:9px 14px;background:{SURF2};border-bottom:1px solid {BORDER};">'
            f'<span style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{TEXT3};">Today\'s Setups</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;'
            f'color:{TEXT3};background:{SURF};border:1px solid {BORDER};'
            f'padding:1px 9px;border-radius:20px;">{len(df)}</span></div>'
            f'<div style="overflow-x:auto;max-height:480px;overflow-y:auto;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            f'<thead><tr>{th_cells}</tr></thead>'
            f'<tbody style="background:{SURF};">{rows_html}</tbody>'
            f'</table></div></div>',
            unsafe_allow_html=True
        )

    render_picks(picks_df)

    # ── Chart ──────────────────────────────────────────────────────────────────
    if picks_df is not None and not picks_df.empty:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        selected = st.selectbox(
            "Quick chart  ·  select a ticker",
            picks_df.sort_values("score", ascending=False)["ticker"].tolist(),
        )
        if selected:
            from data.fetcher import get_ohlcv
            from ta.volatility import BollingerBands as BB
            df_c = get_ohlcv(selected, period="6mo")
            if not df_c.empty:
                _bb = BB(df_c["Close"], window=20, window_dev=2)
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df_c.index,
                    open=df_c["Open"], high=df_c["High"],
                    low=df_c["Low"],   close=df_c["Close"],
                    name=selected,
                    increasing=dict(line=dict(color=BULL, width=1.2), fillcolor="rgba(16,185,129,0.2)"),
                    decreasing=dict(line=dict(color=BEAR, width=1.2), fillcolor="rgba(244,63,94,0.2)")
                ))
                try:
                    ub = _bb.bollinger_hband()
                    lb = _bb.bollinger_lband()
                    fig.add_trace(go.Scatter(x=df_c.index, y=ub,
                        line=dict(color="rgba(34,211,238,0.3)", width=1), showlegend=False))
                    fig.add_trace(go.Scatter(x=df_c.index, y=lb,
                        line=dict(color="rgba(34,211,238,0.3)", width=1),
                        fill="tonexty", fillcolor="rgba(34,211,238,0.04)", showlegend=False))
                except Exception:
                    pass
                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    height=280,
                    paper_bgcolor=SURF, plot_bgcolor=SURF,
                    xaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10), showgrid=True),
                    yaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10), showgrid=True, side="right"),
                    margin=dict(l=0, r=50, t=24, b=0),
                    title=dict(text=f"<b>{selected}</b>  ·  6M", font=dict(color=TEXT, size=13), x=0.01),
                )
                st.plotly_chart(fig, use_container_width=True)
                row  = picks_df[picks_df["ticker"] == selected].iloc[0]
                sigs = row.get("signals_triggered", [])
                if isinstance(sigs, str):
                    sigs = [s.strip() for s in sigs.split(";") if s.strip()]
                if sigs:
                    st.markdown(signal_tags(sigs), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCAN LOGIC
# ══════════════════════════════════════════════════════
if run_clicked:
    from data.universe  import get_universe
    from data.fetcher   import get_ohlcv_batch, get_earnings_days
    from data.research  import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly  import annotate_picks
    from model.predictor import predict_universe
    import db

    tickers = get_universe()
    N = len(tickers)

    with right:
        render_agent("Scan Agent", f"Fetching {N} tickers…", str(N), state="running")
        render_pipeline({})

    with st.spinner(""):
        ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)

    tape = sorted([
        {"ticker": t,
         "price": float(df["Close"].iloc[-1]),
         "chg_pct": (float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2])) /
                    float(df["Close"].iloc[-2]) * 100}
        for t, df in ohlcv_map.items() if not df.empty and len(df) >= 2
    ], key=lambda x: abs(x["chg_pct"]), reverse=True)

    st.session_state["ticker_tape"] = tape
    with right:
        render_tape(tape)
        render_agent("Research Agent", "Reddit · RSS · Alpha Vantage…", str(N), state="running")
        render_pipeline({"universe": N})

    with st.spinner(""):
        blended = research_universe(tickers)
        sentiment_map = {
            t: {
                **blended.get(t, {}),
                "score": round(
                    get_sentiment_with_velocity(t).get("score", 0) * 0.4 +
                    blended.get(t, {}).get("score", 0) * 0.6, 4),
                "velocity": get_sentiment_with_velocity(t).get("velocity", 0),
                "spike": (abs(get_sentiment_with_velocity(t).get("velocity", 0)) >= 0.3 or
                          blended.get(t, {}).get("score", 0) > 0.4),
            } for t in tickers
        }

    with right:
        render_agent("Predict Agent", "XGBoost + blended sentiment…", str(N), state="running")
        render_pipeline({"universe": N, "research": N})

    with st.spinner(""):
        earnings_map = {t: get_earnings_days(t) for t in tickers[:100]}
        picks_df     = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    scored = len(picks_df) if picks_df is not None and not picks_df.empty else 0

    with right:
        render_agent("Risk Agent", "Kelly Criterion sizing…", str(scored), state="running")
        render_pipeline({"universe": N, "research": N, "scored": scored})

    if picks_df is not None and not picks_df.empty:
        picks_df = annotate_picks(picks_df)

    with right:
        render_agent("Learn Agent", "Writing to Supabase…", str(scored), state="running")
        render_pipeline({"universe": N, "research": N, "scored": scored, "risk": scored})

    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows_out = picks_df.copy()
            rows_out["date"]           = datetime.today().strftime("%Y-%m-%d")
            rows_out["actual_move_5d"] = None
            db.append_predictions(rows_out.to_dict(orient="records"))

    scan_time    = datetime.now().strftime("%H:%M")
    final_counts = {"universe": N, "research": N, "scored": scored, "risk": scored, "learn": scored}
    st.session_state.update({
        "last_picks": picks_df, "scan_time": scan_time, "pipeline_counts": final_counts,
    })
    with right:
        render_agent("Scan Agent", f"Completed at {scan_time}", str(scored), state="done")
        render_pipeline(final_counts)
    with left:
        render_picks(picks_df)

    st.rerun()
