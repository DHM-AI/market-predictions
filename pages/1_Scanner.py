import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import (
    inject_css, live_badge,
    GREEN, RED, AMBER, BLUE, CYAN,
    TEXT, TEXT2, TEXT3, CARD, CARD2, BORDER, BORDER2, BG,
)

st.set_page_config(page_title="Market Scanner", page_icon="⚡", layout="wide")
inject_css()

# ── Auto-refresh every 5 min ─────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5 * 60 * 1000, key="autorefresh")
except Exception:
    pass

st.markdown(f"""
<style>
/* ─── Filter pipeline ───────────────────── */
.filter-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    overflow:hidden; margin-bottom:10px;
}}
.filter-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER}; background:{CARD2};
}}
.fhdr-title {{ font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{TEXT3}; }}
.filter-row {{
    display:grid; grid-template-columns:10px 150px 1fr 46px;
    align-items:center; gap:10px; padding:10px 14px;
    border-bottom:1px solid rgba(255,255,255,0.03);
}}
.filter-row:last-child {{ border-bottom:none; }}
.f-dot-on  {{ width:8px;height:8px;border-radius:50%;background:{GREEN};box-shadow:0 0 8px {GREEN}55; }}
.f-dot-off {{ width:8px;height:8px;border-radius:50%;background:transparent;border:1.5px solid {TEXT3}; }}
.f-name    {{ font-size:12px; font-weight:600; color:{TEXT}; }}
.f-desc    {{ font-size:10px; color:{TEXT3}; }}
.f-bar     {{ width:100%;height:4px;background:{BORDER2};border-radius:2px; }}
.f-fill    {{ height:4px;border-radius:2px;background:{GREEN}; }}
.f-count   {{ font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;text-align:right; }}

/* ─── Agent card ────────────────────────── */
.agent-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:14px 16px; margin-bottom:10px;
}}
.agent-label {{ font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEXT3};margin-bottom:6px; }}
.agent-row   {{ display:flex;justify-content:space-between;align-items:center; }}
.agent-name  {{ font-size:14px;font-weight:700;color:{TEXT};display:flex;align-items:center;gap:8px; }}
.agent-sub   {{ font-size:11px;color:{TEXT3};margin-top:5px; }}
.agent-count {{ font-family:'JetBrains Mono',monospace;font-size:38px;font-weight:700;line-height:1; }}

/* ─── Qualified ─────────────────────────── */
.qual {{
    background:rgba(0,255,136,0.05); border:1px solid rgba(0,255,136,0.2);
    border-radius:8px; padding:10px 16px; margin-bottom:10px;
    display:flex; justify-content:space-between; align-items:center;
}}
.qual-label {{ font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{GREEN}; }}
.qual-sub   {{ font-size:11px;color:{TEXT3};margin-top:3px; }}
.qual-num   {{ font-family:'JetBrains Mono',monospace;font-size:34px;font-weight:700;color:{GREEN}; }}

/* ─── Feed ──────────────────────────────── */
.feed-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    overflow:hidden; margin-bottom:10px;
}}
.feed-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER}; background:{CARD2};
}}
.feed-item {{
    padding:9px 14px; border-bottom:1px solid rgba(255,255,255,0.03);
}}
.feed-item:last-child {{ border-bottom:none; }}
.feed-meta   {{ font-size:10px; color:{TEXT3}; margin-bottom:3px; display:flex; align-items:center; gap:6px; }}
.feed-src    {{ font-weight:700; color:{TEXT2}; }}
.feed-text   {{ font-size:12px; color:{TEXT}; line-height:1.4; }}
.tag-bull    {{ background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.25);color:{GREEN};font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px; }}
.tag-bear    {{ background:rgba(255,59,92,0.1);border:1px solid rgba(255,59,92,0.25);color:{RED};font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px; }}

/* ─── Tape ──────────────────────────────── */
.tape-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
}}
.tape-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 14px; border-bottom:1px solid {BORDER}; background:{CARD2};
}}
.tape-hdr-t {{ font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEXT3}; }}
.tape-row {{
    display:grid; grid-template-columns:58px 1fr 50px;
    align-items:center; gap:6px; padding:6px 14px;
    border-bottom:1px solid rgba(255,255,255,0.025);
}}
.tape-row:last-child {{ border-bottom:none; }}
.tape-row:hover {{ background:rgba(255,255,255,0.02); }}
.t-sym {{ font-family:'JetBrains Mono',monospace;font-weight:700;color:{GREEN};font-size:12px; }}
.t-px  {{ font-family:'JetBrains Mono',monospace;font-size:11px;color:{TEXT3};text-align:right;padding-right:6px; }}
.t-up  {{ font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:{GREEN};text-align:right; }}
.t-dn  {{ font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:{RED};text-align:right; }}

/* ─── Pick cards ────────────────────────── */
.pick-card {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:14px; display:flex; flex-direction:column; gap:10px;
}}
.pick-top    {{ display:flex; justify-content:space-between; align-items:flex-start; }}
.pick-ticker {{ font-family:'JetBrains Mono',monospace; font-size:22px; font-weight:700; color:{GREEN}; }}
.pick-score  {{ font-family:'JetBrains Mono',monospace; font-size:30px; font-weight:700; line-height:1; text-align:right; }}
.pick-slabel {{ font-size:9px; color:{TEXT3}; letter-spacing:1px; text-align:right; margin-top:2px; }}
.pick-div    {{ height:1px; background:{BORDER}; }}
.bar-row     {{ display:flex; flex-direction:column; gap:5px; }}
.bar-item    {{ display:flex; align-items:center; gap:8px; }}
.bar-lbl     {{ font-size:10px; color:{TEXT3}; width:78px; flex-shrink:0; }}
.bar-track   {{ flex:1; height:4px; background:{BORDER2}; border-radius:2px; }}
.bar-fill    {{ height:4px; border-radius:2px; }}
.bar-pct     {{ font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; min-width:28px; text-align:right; }}
.pick-stats  {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:5px; }}
.pk-s        {{ display:flex; flex-direction:column; gap:2px; }}
.pk-sl       {{ font-size:9px; color:{TEXT3}; text-transform:uppercase; letter-spacing:1px; }}
.pk-sv       {{ font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:600; color:{TEXT}; }}
.kelly-row   {{
    display:flex; justify-content:space-between; align-items:center;
    background:{CARD2}; border-radius:5px; padding:8px 10px;
}}
.kelly-lbl   {{ font-size:10px; color:{TEXT3}; }}
.kelly-val   {{ font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:700; color:{GREEN}; }}

/* ─── No data ───────────────────────────── */
.nodata {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:60px 20px; text-align:center;
}}
.nodata-icon  {{ font-size:32px; opacity:0.3; margin-bottom:12px; }}
.nodata-title {{ font-size:15px; font-weight:600; color:{TEXT2}; margin-bottom:6px; }}
.nodata-body  {{ font-size:12px; color:{TEXT3}; line-height:1.7; }}

@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("picks_df", None), ("filter_counts", {}),
              ("tape", []), ("scan_time", ""), ("feeds", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Always load from Supabase on render ──────────────────────────────────────
picks_df = st.session_state["picks_df"]
last_github_run = ""
try:
    from db import load_predictions_for_date, load_predictions, db_available
    if db_available():
        today_rows = load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
        if today_rows:
            picks_df = pd.DataFrame(today_rows)
            st.session_state["picks_df"] = picks_df
            if "created_at" in picks_df.columns:
                ts = pd.to_datetime(picks_df["created_at"].iloc[0])
                last_github_run = ts.strftime("%H:%M")
except Exception:
    pass

n_picks = len(picks_df) if picks_df is not None and not picks_df.empty else 0
fc = st.session_state["filter_counts"]
scan_time = st.session_state["scan_time"] or last_github_run

# ── LAYOUT ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="medium")

# ════════════════════ RIGHT ═══════════════════════
with col_right:
    feed_ph = st.empty()
    tape_ph = st.empty()

    def render_feed(feeds):
        if not feeds:
            feed_ph.markdown(
                f'<div class="feed-card">'
                f'<div class="feed-hdr"><span class="fhdr-title">Signal Feeds</span>'
                f'<span style="font-size:9px;color:{TEXT3};font-weight:700;letter-spacing:1px;">WAITING</span></div>'
                f'<div style="padding:28px 14px;text-align:center;">'
                f'<div style="font-size:11px;color:{TEXT3};">Reddit · RSS · Alpha Vantage headlines<br>appear here when agent runs</div>'
                f'</div></div>', unsafe_allow_html=True)
            return
        items = ""
        for f in feeds[:6]:
            bias  = f.get("bias", "")
            tag   = (f'<span class="tag-bull">BULL</span>' if bias == "bullish" else
                     f'<span class="tag-bear">BEAR</span>' if bias == "bearish" else "")
            items += (
                f'<div class="feed-item">'
                f'<div class="feed-meta"><span class="feed-src">{f.get("source","")}</span>'
                f'<span>·</span><span>{f.get("ticker","")}</span>{tag}</div>'
                f'<div class="feed-text">{str(f.get("text",""))[:110]}</div>'
                f'</div>')
        feed_ph.markdown(
            f'<div class="feed-card">'
            f'<div class="feed-hdr"><span class="fhdr-title">Signal Feeds</span>'
            f'<span style="font-size:9px;color:{GREEN};font-weight:700;letter-spacing:1px;">● LIVE</span></div>'
            f'{items}</div>', unsafe_allow_html=True)

    def render_tape(data):
        if not data:
            tape_ph.markdown(
                f'<div class="tape-card">'
                f'<div class="tape-hdr"><span class="tape-hdr-t">Universe</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">—</span></div>'
                f'<div style="padding:28px 14px;text-align:center;">'
                f'<div style="font-size:11px;color:{TEXT3};">Populates when agent runs</div>'
                f'</div></div>', unsafe_allow_html=True)
            return
        rows = ""
        for t in data[:30]:
            chg  = t.get("chg_pct", 0)
            cls  = "t-up" if chg >= 0 else "t-dn"
            sign = "+" if chg >= 0 else ""
            px   = f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows += (f'<div class="tape-row">'
                     f'<span class="t-sym">{t["ticker"]}</span>'
                     f'<span class="t-px">{px}</span>'
                     f'<span class="{cls}">{sign}{chg:.1f}%</span>'
                     f'</div>')
        tape_ph.markdown(
            f'<div class="tape-card">'
            f'<div class="tape-hdr"><span class="tape-hdr-t">Universe</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{TEXT3};">{len(data)}</span></div>'
            f'<div style="overflow-y:auto;max-height:340px;">{rows}</div></div>',
            unsafe_allow_html=True)

    render_feed(st.session_state["feeds"])
    render_tape(st.session_state["tape"])

# ════════════════════ LEFT ════════════════════════
with col_left:
    agent_ph  = st.empty()
    filter_ph = st.empty()
    qual_ph   = st.empty()

    # Status: determine if agent ran today via GitHub Actions
    if n_picks > 0:
        agent_state = "done"
        agent_sub   = f"GitHub Actions completed · {n_picks} setups written to Supabase"
    else:
        agent_state = "idle"
        agent_sub   = "Runs automatically at 8:00 AM ET via GitHub Actions"

    def render_agent(sub, count, state):
        c     = GREEN if state in ("done","running") else TEXT3
        pulse = "animation:blink 0.7s infinite;" if state == "running" else ""
        agent_ph.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-label">Market Scan Agent</div>'
            f'<div class="agent-row">'
            f'<div>'
            f'<div class="agent-name">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;{pulse}"></span>'
            f'{"Running" if state=="running" else "Complete" if state=="done" else "Scheduled · 8 AM ET weekdays"}'
            f'</div>'
            f'<div class="agent-sub">{sub}</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div class="agent-count" style="color:{c};">{count}</div>'
            f'<div style="font-size:9px;color:{TEXT3};letter-spacing:1px;margin-top:2px;">SETUPS</div>'
            f'</div></div></div>', unsafe_allow_html=True)

    def render_filters(fc, N=509):
        filters = [
            ("Liquidity Screen",  "Price > $5 · Volume > 500k",          fc.get("universe",  0), N,                           bool(fc.get("universe"))),
            ("BB Compression",    "Squeeze below 10th percentile",        fc.get("bb",        0), fc.get("universe", N) or N,  bool(fc.get("bb"))),
            ("Volume Surge",      "2× above 20-day average",              fc.get("volume",    0), fc.get("bb",        N) or N, bool(fc.get("volume"))),
            ("Sentiment Spike",   "Reddit + RSS score + velocity",        fc.get("sentiment", 0), fc.get("volume",    N) or N, bool(fc.get("sentiment"))),
            ("Edge Detection",    "Blended score ≥ 50 · target 5%+",     fc.get("edge",      0), fc.get("sentiment", N) or N, bool(fc.get("edge"))),
        ]
        n_done = sum(1 for *_, d in filters if d)
        done_c = GREEN if n_done == 5 else (AMBER if n_done > 0 else TEXT3)
        rows = ""
        for name, desc, cnt, total, done in filters:
            dot = "f-dot-on" if done else "f-dot-off"
            nc  = GREEN if done else TEXT3
            cs  = str(cnt) if done else "—"
            bw  = int((cnt / total) * 100) if (done and total and cnt) else 0
            rows += (
                f'<div class="filter-row">'
                f'<div class="{dot}"></div>'
                f'<div><div class="f-name">{name}</div><div class="f-desc">{desc}</div></div>'
                f'<div class="f-bar"><div class="f-fill" style="width:{bw}%;"></div></div>'
                f'<div class="f-count" style="color:{nc};">{cs}</div>'
                f'</div>')
        filter_ph.markdown(
            f'<div class="filter-card">'
            f'<div class="filter-hdr"><span class="fhdr-title">Filter Pipeline</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{done_c};">{n_done}/5</span></div>'
            f'{rows}</div>', unsafe_allow_html=True)

    def render_qual(n):
        if n > 0:
            qual_ph.markdown(
                f'<div class="qual">'
                f'<div><div class="qual-label">Qualified Setups</div>'
                f'<div class="qual-sub">Score ≥ 50 · Expected move 5%+</div></div>'
                f'<div class="qual-num">{n}</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            qual_ph.empty()

    render_agent(agent_sub, str(n_picks) if n_picks else "—", agent_state)
    render_filters(fc)
    render_qual(n_picks)

# ════════════════ PICK CARDS ══════════════════════
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

if picks_df is not None and not picks_df.empty:
    sorted_df = picks_df.sort_values("score", ascending=False)
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEXT3};">'
        f'Today\'s Setups &nbsp;·&nbsp; {datetime.today().strftime("%b %d %Y")}</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;background:{CARD2};'
        f'border:1px solid {BORDER};color:{TEXT3};padding:1px 8px;border-radius:20px;">{len(sorted_df)} found</span>'
        f'</div>', unsafe_allow_html=True)

    rows_df = [sorted_df.iloc[i:i+3] for i in range(0, len(sorted_df), 3)]
    for row_chunk in rows_df:
        cols = st.columns(3)
        for ci, (_, row) in enumerate(row_chunk.iterrows()):
            ticker = row.get("ticker", "")
            score  = float(row.get("score", 0))
            direct = row.get("direction", "mixed")
            conf   = row.get("confidence", "—")
            dur    = row.get("duration", "—")
            rsi    = row.get("rsi", 0) or 0
            vol    = row.get("volume_ratio", 0) or 0
            kelly  = row.get("dollar_amount", 0) or 0
            bb_pct = row.get("bb_pct", 0) or 0
            sent   = row.get("sentiment_score", 0) or 0
            xgb    = row.get("xgb_prob", 0) or 0

            if direct == "bullish":
                dlabel, dc, dborder, lborder = "↑ LONG",  GREEN, "rgba(0,255,136,0.3)",  GREEN
            elif direct == "bearish":
                dlabel, dc, dborder, lborder = "↓ SHORT", RED,   "rgba(255,59,92,0.3)",  RED
            else:
                dlabel, dc, dborder, lborder = "◆ WATCH", AMBER, "rgba(245,158,11,0.3)", AMBER

            sc = GREEN if score >= 70 else AMBER if score >= 50 else TEXT3

            # Signal bars
            bb_v   = max(0, min(100, int((1 - bb_pct) * 100))) if bb_pct else int(score * 0.8)
            vol_v  = max(0, min(100, int((vol / 4) * 100)))     if vol else int(score * 0.6)
            sent_v = max(0, min(100, int((sent + 1) * 50)))     if sent else int(score * 0.55)
            xgb_v  = max(0, min(100, int(xgb * 100)))           if xgb else int(score * 0.72)

            def brow(lbl, pct, color):
                return (f'<div class="bar-item">'
                        f'<span class="bar-lbl">{lbl}</span>'
                        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color};box-shadow:0 0 4px {color}44;"></div></div>'
                        f'<span class="bar-pct" style="color:{color};">{pct}%</span>'
                        f'</div>')

            ks = f"${kelly:,.0f}" if kelly else "—"
            rs = f"{float(rsi):.0f}" if rsi else "—"
            vs = f"{float(vol):.1f}×" if vol else "—"
            cc = {"High": GREEN, "Medium": AMBER, "Low": TEXT3}.get(conf, TEXT3)

            html = (
                f'<div class="pick-card" style="border-left:2px solid {lborder};">'

                f'<div class="pick-top">'
                f'<div>'
                f'<div class="pick-ticker">{ticker}</div>'
                f'<div style="margin-top:6px;">'
                f'<span style="background:rgba(0,0,0,0.3);border:1px solid {dborder};color:{dc};'
                f'font-size:10px;font-weight:700;letter-spacing:1px;padding:2px 8px;border-radius:3px;">{dlabel}</span>'
                f'</div></div>'
                f'<div><div class="pick-score" style="color:{sc};">{score:.0f}</div>'
                f'<div class="pick-slabel">/ 100</div></div>'
                f'</div>'

                f'<div class="pick-div"></div>'

                f'<div class="bar-row">'
                + brow("BB Squeeze",  bb_v,   BLUE)
                + brow("Volume",      vol_v,  AMBER)
                + brow("Sentiment",   sent_v, CYAN)
                + brow("XGBoost",     xgb_v,  GREEN)
                + f'</div>'

                f'<div class="pick-div"></div>'

                f'<div class="pick-stats">'
                f'<div class="pk-s"><span class="pk-sl">RSI</span><span class="pk-sv">{rs}</span></div>'
                f'<div class="pk-s"><span class="pk-sl">Volume</span><span class="pk-sv">{vs}</span></div>'
                f'<div class="pk-s"><span class="pk-sl">Window</span><span class="pk-sv" style="font-size:11px;">{dur}</span></div>'
                f'</div>'

                f'<div class="kelly-row">'
                f'<span class="kelly-lbl">Kelly Position &nbsp;<span style="color:{cc};font-weight:600;font-size:10px;">{conf}</span></span>'
                f'<span class="kelly-val">{ks}</span>'
                f'</div>'

                f'</div>'
            )
            with cols[ci]:
                st.markdown(html, unsafe_allow_html=True)

    # ── Chart ─────────────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    sel = st.selectbox("", sorted_df["ticker"].tolist(), label_visibility="collapsed")
    if sel:
        from data.fetcher import get_ohlcv
        from ta.volatility import BollingerBands as BB
        df_c = get_ohlcv(sel, period="6mo")
        if not df_c.empty:
            _bb = BB(df_c["Close"], window=20, window_dev=2)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_c.index, open=df_c["Open"], high=df_c["High"],
                low=df_c["Low"], close=df_c["Close"], name=sel,
                increasing=dict(line=dict(color=GREEN, width=1), fillcolor="rgba(0,255,136,0.15)"),
                decreasing=dict(line=dict(color=RED,   width=1), fillcolor="rgba(255,59,92,0.15)")))
            try:
                fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_hband(),
                    line=dict(color="rgba(0,255,136,0.2)", width=1), showlegend=False))
                fig.add_trace(go.Scatter(x=df_c.index, y=_bb.bollinger_lband(),
                    line=dict(color="rgba(0,255,136,0.2)", width=1),
                    fill="tonexty", fillcolor="rgba(0,255,136,0.03)", showlegend=False))
            except Exception:
                pass
            fig.update_layout(
                xaxis_rangeslider_visible=False, height=300,
                paper_bgcolor=CARD, plot_bgcolor=CARD,
                xaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10)),
                yaxis=dict(gridcolor=BORDER, tickfont=dict(color=TEXT3, size=10), side="right"),
                margin=dict(l=0, r=48, t=22, b=0),
                title=dict(text=f"<b>{sel}</b>  ·  6M", font=dict(color=TEXT, size=12), x=0.01))
            st.plotly_chart(fig, use_container_width=True)

else:
    st.markdown(
        f'<div class="nodata">'
        f'<div class="nodata-icon">⏳</div>'
        f'<div class="nodata-title">Waiting for today\'s scan</div>'
        f'<div class="nodata-body">'
        f'The agent runs automatically every weekday at <strong style="color:{TEXT2};">8:00 AM ET</strong> via GitHub Actions.<br>'
        f'Results appear here automatically — no action needed.<br><br>'
        f'<span style="color:{AMBER};">⚠ GitHub Actions secrets need to be configured to activate automatic scanning.</span>'
        f'</div></div>', unsafe_allow_html=True)
