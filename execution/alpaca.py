from __future__ import annotations
"""
Alpaca execution module — bracket orders with automatic stop loss + take profit.

Every trade placed is a BRACKET ORDER:
  - Entry at market
  - Stop loss:   -3% from entry  (long) / +3% (short)
  - Take profit: +5% from entry  (long) / -5% (short)

Alpaca monitors these automatically — you don't need to watch.

SAFETY DEFAULTS:
  - Paper trading mode unless ALPACA_LIVE_MODE=true
  - Max single position: 10% of bankroll (Kelly hard cap)
  - Daily loss limit: 5% — agent stops all trading if hit
  - Minimum score ≥ 70 for auto-execution
  - All trades logged to Supabase

To enable live trading:
  Set ALPACA_BASE_URL=https://api.alpaca.markets AND ALPACA_LIVE_MODE=true
  DO NOT go live before 30 days of paper trading validation.
"""
import os
from datetime import datetime
from config import (BANKROLL, ALPACA_API_KEY, ALPACA_SECRET_KEY,
                    ALPACA_BASE_URL, ALPACA_LIVE_MODE,
                    MAX_POSITION_PCT, DAILY_LOSS_LIMIT_PCT,
                    KELLY_LOSS_PCT, MOVE_TARGET_PCT)


def _get_client():
    try:
        from alpaca.trading.client import TradingClient
        return TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY,
                             paper=not ALPACA_LIVE_MODE)
    except ImportError:
        raise RuntimeError("alpaca-py not installed. Run: pip install alpaca-py")


def is_configured() -> bool:
    return bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)


def is_live_mode() -> bool:
    return ALPACA_LIVE_MODE


def get_account() -> dict:
    client = _get_client()
    acct = client.get_account()
    # daytrading_buying_power is what bracket orders (TimeInForce.DAY) actually
    # consume. Different from regt_buying_power (overnight) and buying_power
    # (overall). With many open positions, DT-BP is what gets exhausted first.
    dt_bp = getattr(acct, "daytrading_buying_power", None) or getattr(acct, "day_trading_buying_power", None)
    return {
        "buying_power":            float(acct.buying_power),
        "daytrading_buying_power": float(dt_bp) if dt_bp is not None else float(acct.buying_power),
        "regt_buying_power":       float(getattr(acct, "regt_buying_power", acct.buying_power)),
        "portfolio_value":         float(acct.portfolio_value),
        "cash":                    float(acct.cash),
        "equity":                  float(acct.equity),
        "last_equity":             float(acct.last_equity) if acct.last_equity else float(acct.equity),
        "paper":                   not ALPACA_LIVE_MODE,
    }


# ── Active order statuses (CRITICAL: covers all SDK string formats) ──────
# The Alpaca Python SDK can stringify an OrderStatus enum two ways:
#   "OrderStatus.HELD"  or  "held"
# Some statuses (ACCEPTED, PENDING_NEW) have bitten us repeatedly when only
# one form was listed. ALWAYS use this set for "is this order active?".
ACTIVE_ORDER_STATUSES = {
    "open", "new", "held", "pending_new", "accepted",
    "orderstatus.open", "orderstatus.new", "orderstatus.held",
    "orderstatus.pending_new", "orderstatus.accepted",
}


def is_active_order(o) -> bool:
    """Single source of truth: is this order currently active (held/open/etc)?"""
    return str(getattr(o, "status", "")).lower() in ACTIVE_ORDER_STATUSES


# ── Order-status normalization ─────────────────────────────────────────────
# Audit C-3/C-4/C-5: Three safety controls (MAX_DAILY_TRADES counter,
# DUSK day-trade detector, ZEUS audit) were silently broken because
# `str(OrderStatus.FILLED) == "OrderStatus.FILLED"`, never `"filled"`.
# Use this helper EVERYWHERE you compare order.status against literals.
def order_status(o) -> str:
    """Normalize Alpaca order status to a plain lowercase string.

    Handles both string forms the SDK emits:
        "filled"             → "filled"
        "OrderStatus.FILLED" → "filled"
    """
    return str(getattr(o, "status", "")).lower().replace("orderstatus.", "")


# Buying power safety factor — leaves headroom for slippage and same-scan orders
_BP_SAFETY_FACTOR = 0.90
# In-process cache: once DT-BP is found exhausted, short-circuit the rest of
# the scan so we don't fire 10 redundant API calls + log lines.
_dt_bp_exhausted_for_scan = False


def reset_bp_cache() -> None:
    """Call at start of each scan so the cache doesn't persist across scans."""
    global _dt_bp_exhausted_for_scan
    _dt_bp_exhausted_for_scan = False


def _check_buying_power(dollar_amount: float, ticker: str,
                        notify: bool = True) -> tuple[bool, str]:
    """
    Pre-trade DT-BP check. Returns (ok, reason).
    Bracket orders (TimeInForce.DAY) consume daytrading_buying_power.
    Reject early if the trade would exceed 90% of available DT-BP.

    notify: when True (default), posts a Slack alert ONCE per scan when
            DT-BP first hits exhaustion. Set False from diagnostic/test
            callers to avoid polluting Slack.
    """
    global _dt_bp_exhausted_for_scan
    if _dt_bp_exhausted_for_scan:
        return False, "day-trading buying power exhausted earlier in this scan"
    try:
        acct = get_account()
        dt_bp = acct.get("daytrading_buying_power", 0)
        usable = dt_bp * _BP_SAFETY_FACTOR
        if dollar_amount > usable:
            # Mark exhausted so subsequent orders short-circuit
            _dt_bp_exhausted_for_scan = True
            # Notify Slack once per process (not per ticker spam, not for tests)
            if notify:
                try:
                    from alerts.slack import _post
                    _post({
                        "text": (
                            f"⚠️ *DT-BP exhausted* — skipping remaining trades this scan\n"
                            f"> Available: ${dt_bp:,.0f}  ·  Need: ${dollar_amount:,.0f}  ·  "
                            f"Tried: `{ticker}`\n"
                            f"> Close some positions or wait until next session."
                        ),
                    })
                except Exception:
                    pass
            return False, (
                f"insufficient day-trading buying power "
                f"(need ${dollar_amount:,.0f}, have ${dt_bp:,.0f}, "
                f"usable ${usable:,.0f})"
            )
        return True, ""
    except Exception as e:
        return False, f"BP check failed: {e}"


def get_current_price(ticker: str) -> float | None:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        req   = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quote = data_client.get_stock_latest_quote(req)
        return float(quote[ticker].ask_price)
    except Exception:
        return None


def _check_daily_loss_limit() -> bool:
    """Returns True if safe to trade, False if daily loss limit breached."""
    try:
        acct        = _get_client().get_account()
        equity      = float(acct.equity)
        last_equity = float(acct.last_equity)
        daily_loss  = (equity - last_equity) / last_equity
        if daily_loss < -DAILY_LOSS_LIMIT_PCT:
            print(f"[APEX] ⚠ Daily loss limit breached ({daily_loss:.1%}). Halting trades.")
            return False
        return True
    except Exception as e:
        print(f"[APEX] ⚠ Could not check daily loss limit ({e}) — blocking trades for safety.")
        return False  # fail closed — never trade blind


def place_order(ticker: str, dollar_amount: float, direction: str,
                reason: str = "", execution_path: str = "") -> dict:
    """
    Place a BRACKET ORDER: entry + stop loss + take profit in one shot.

    Stop loss:   KELLY_LOSS_PCT  below entry for longs  (default 3%)
    Take profit: MOVE_TARGET_PCT above entry for longs  (default 5%)
    Reversed for shorts.
    """
    if not is_configured():
        return {"status": "skipped", "reason": "Alpaca not configured"}

    if not _check_daily_loss_limit():
        return {"status": "halted", "reason": "Daily loss limit breached (5%). No new trades today."}

    # Cap position size
    max_allowed = BANKROLL * MAX_POSITION_PCT
    if dollar_amount > max_allowed:
        dollar_amount = max_allowed

    # ── Pre-trade day-trading buying-power check ──────────────────────────
    # Bracket orders consume DT-BP, not regular BP. With 10+ positions open
    # this gets exhausted fast. Skipping early avoids the noisy Slack-spam
    # of 10 simultaneous "insufficient day trading buying power" failures.
    bp_ok, bp_reason = _check_buying_power(dollar_amount, ticker)
    if not bp_ok:
        print(f"[APEX] {ticker} skipped — {bp_reason}")
        return {"status": "skipped", "ticker": ticker, "reason": bp_reason}

    mode = "LIVE" if is_live_mode() else "PAPER"
    side = "buy" if direction == "bullish" else "sell"

    # For short orders, verify the asset is actually shortable on Alpaca
    # before attempting — avoids code 42210000 "asset cannot be sold short"
    if side == "sell":
        try:
            asset = _get_client().get_asset(ticker)
            if not getattr(asset, "shortable", False):
                print(f"[APEX] {ticker} is not shortable on Alpaca — skipping bearish order")
                return {"status": "skipped",
                        "reason": f"{ticker} is not shortable on Alpaca",
                        "ticker": ticker}
            if not getattr(asset, "easy_to_borrow", False):
                print(f"[APEX] {ticker} is hard-to-borrow — skipping bearish order")
                return {"status": "skipped",
                        "reason": f"{ticker} is hard-to-borrow",
                        "ticker": ticker}
        except Exception as e:
            print(f"[APEX] Could not verify shortability for {ticker}: {e} — skipping")
            return {"status": "skipped",
                    "reason": f"Could not verify shortability for {ticker}",
                    "ticker": ticker}

    # Get current price to calculate SL/TP and convert notional → shares
    price = get_current_price(ticker)

    # Fallback: try yfinance if Alpaca data feed fails.
    # N-9 fix: yfinance.download() doesn't expose a `timeout` param so a
    # stalled HTTP call can hang the whole scan past CF Workers' 30s wall.
    # Run it in a daemon thread with a hard 5s timeout — if it doesn't return,
    # skip the trade rather than stalling.
    if price is None or price <= 0:
        try:
            import threading
            _result = [None]
            def _yf_fetch():
                try:
                    import yfinance as yf
                    hist = yf.download(ticker, period="1d", interval="1m",
                                       progress=False, auto_adjust=True)
                    if not hist.empty:
                        _result[0] = float(hist["Close"].iloc[-1])
                except Exception:
                    pass
            _th = threading.Thread(target=_yf_fetch, daemon=True)
            _th.start()
            _th.join(timeout=5.0)
            if _result[0] is not None:
                price = _result[0]
                print(f"[APEX] Used yfinance price for {ticker}: ${price:.2f}")
            elif _th.is_alive():
                print(f"[APEX] yfinance price fetch for {ticker} timed out (5s) — skipping")
        except Exception as _ye:
            print(f"[APEX] yfinance fallback failed for {ticker}: {_ye}")

    if price is None or price <= 0:
        print(f"[APEX] Could not get price for {ticker} — skipping (no unprotected order placed)")
        return {"status": "skipped", "reason": f"Could not fetch price for {ticker}"}

    qty = max(1, round(dollar_amount / price))

    # Stop loss and take profit prices
    if side == "buy":
        stop_price  = round(price * (1 - KELLY_LOSS_PCT), 2)
        limit_price = round(price * (1 + MOVE_TARGET_PCT), 2)
    else:
        stop_price  = round(price * (1 + KELLY_LOSS_PCT), 2)
        limit_price = round(price * (1 - MOVE_TARGET_PCT), 2)

    print(f"[APEX] [{mode}] BRACKET {side.upper()} {qty} {ticker} @ ~${price:.2f}")
    print(f"         Stop loss: ${stop_price:.2f} ({KELLY_LOSS_PCT*100:.0f}% risk)")
    print(f"         Take profit: ${limit_price:.2f} ({MOVE_TARGET_PCT*100:.0f}% target)")

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import (MarketOrderRequest,
                                              TakeProfitRequest, StopLossRequest)
        from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

        client    = _get_client()
        order_req = MarketOrderRequest(
            symbol         = ticker,
            qty            = qty,
            side           = OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force  = TimeInForce.DAY,   # Alpaca requires DAY for bracket orders
            order_class    = OrderClass.BRACKET,
            take_profit    = TakeProfitRequest(limit_price=limit_price),
            stop_loss      = StopLossRequest(stop_price=stop_price),
        )
        order = client.submit_order(order_req)

        result = {
            "status":        "submitted",
            "order_id":      str(order.id),
            "ticker":        ticker,
            "side":          side,
            "qty":           qty,
            "entry_price":   price,
            "stop_loss":     stop_price,
            "take_profit":   limit_price,
            "dollar_amount": round(qty * price, 2),
            "mode":          mode,
            "timestamp":     datetime.now().isoformat(),
            "reason":        reason,
            "execution_path": execution_path,
        }

        try:
            import db
            if db.db_available():
                db.save_trade(result)
        except Exception:
            pass

        return result

    except Exception as e:
        err_str = str(e)
        # Alpaca rejects when our estimated price differs from actual market price.
        # Parse base_price from error and retry with corrected stop/TP.
        if "base_price" in err_str and "stop_price" in err_str:
            try:
                import json, re
                m = re.search(r'"base_price"\s*:\s*"?([\d.]+)"?', err_str)
                if m:
                    actual_price = float(m.group(1))
                    if side == "buy":
                        stop_price  = round(actual_price * (1 - KELLY_LOSS_PCT), 2)
                        limit_price = round(actual_price * (1 + MOVE_TARGET_PCT), 2)
                    else:
                        stop_price  = round(actual_price * (1 + KELLY_LOSS_PCT), 2)
                        limit_price = round(actual_price * (1 - MOVE_TARGET_PCT), 2)
                    qty = max(1, round(dollar_amount / actual_price))
                    print(f"[APEX] Retrying bracket with corrected price ${actual_price:.2f} "
                          f"→ SL ${stop_price:.2f} / TP ${limit_price:.2f}")
                    from alpaca.trading.client import TradingClient
                    from alpaca.trading.requests import (MarketOrderRequest,
                                                          TakeProfitRequest, StopLossRequest)
                    from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
                    client    = _get_client()
                    order_req = MarketOrderRequest(
                        symbol        = ticker,
                        qty           = qty,
                        side          = OrderSide.BUY if side == "buy" else OrderSide.SELL,
                        time_in_force = TimeInForce.DAY,
                        order_class   = OrderClass.BRACKET,
                        take_profit   = TakeProfitRequest(limit_price=limit_price),
                        stop_loss     = StopLossRequest(stop_price=stop_price),
                    )
                    order = client.submit_order(order_req)
                    result = {
                        "status": "submitted", "order_id": str(order.id),
                        "ticker": ticker, "side": side, "qty": qty,
                        "entry_price": actual_price, "stop_loss": stop_price,
                        "take_profit": limit_price,
                        "dollar_amount": round(qty * actual_price, 2),
                        "mode": mode, "timestamp": datetime.now().isoformat(),
                        "reason": reason, "execution_path": execution_path,
                    }
                    try:
                        import db
                        if db.db_available():
                            db.save_trade(result)
                    except Exception:
                        pass
                    return result
            except Exception as retry_err:
                print(f"[APEX] Bracket retry failed: {retry_err}")
        # H-7 fix: do NOT blindly fall back to a NAKED simple order on every
        # bracket failure. Only fall back for KNOWN-RECOVERABLE errors. For
        # anything else, refuse and Slack-alert — naked positions are worse
        # than missed trades.
        # R-1 fix: explicit parens — Python's `and` binds tighter than `or`,
        # but readability + future-proofing matters; also tightened the
        # base_price match to require an Alpaca-specific phrase rather than
        # any error string that happens to contain "base_price".
        _err_lc = str(e).lower()
        _recoverable = (
            ("base_price" in _err_lc and "stop" in _err_lc)
            or ("stop_loss"   in _err_lc and "must be" in _err_lc)
            or ("take_profit" in _err_lc and "must be" in _err_lc)
        )
        if _recoverable:
            print(f"[APEX] Bracket failed ({e}) — recoverable, falling back to simple order.")
            return _place_simple_order(ticker, dollar_amount, side, mode, reason)
        # Non-recoverable — refuse and alert
        print(f"[APEX] Bracket failed ({e}) — NOT falling back (would create naked position).")
        try:
            from alerts.slack import _post
            _post({"text": (
                f"🚨 *Bracket order REFUSED — {ticker}*\n"
                f">Error: `{e}`\n"
                f">Did NOT fall back to simple order (would leave position unprotected)."
            )})
        except Exception:
            pass
        return {"status": "rejected_bracket_unknown", "ticker": ticker,
                "reason": f"Bracket failed with non-recoverable error: {e}"}


def _place_simple_order(ticker: str, dollar_amount: float, side: str,
                         mode: str, reason: str) -> dict:
    """Fallback: plain market order without bracket (futures, etc.)

    For SELL (short) orders we always use qty — Alpaca rejects notional shorts.
    For BUY orders we prefer notional, fall back to qty if needed.
    """
    # CRITICAL audit C-10: daily-loss kill switch was only checked in place_order.
    # Fallback paths bypassed it — bracket failure could keep bleeding capital
    # past the documented 5% hard limit. Check here too.
    if not _check_daily_loss_limit():
        return {"status": "rejected_loss_limit",
                "reason": "Daily loss limit hit — simple-order path also halted"}
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        client     = _get_client()
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

        # Shorts must use qty (whole shares) — Alpaca forbids fractional shorts
        if side == "sell":
            price = get_current_price(ticker)
            if not price or price <= 0:
                return {"status": "error",
                        "reason": f"Could not fetch price for {ticker} (short order)",
                        "ticker": ticker}
            qty       = max(1, round(dollar_amount / price))
            order_req = MarketOrderRequest(
                symbol        = ticker,
                qty           = qty,
                side          = order_side,
                time_in_force = TimeInForce.DAY,
            )
        else:
            qty       = None
            order_req = MarketOrderRequest(
                symbol        = ticker,
                notional      = round(dollar_amount, 2),
                side          = order_side,
                time_in_force = TimeInForce.DAY,
            )

        order  = client.submit_order(order_req)
        actual_qty = qty or round(dollar_amount / (get_current_price(ticker) or 1))
        result = {
            "status": "submitted", "order_id": str(order.id),
            "ticker": ticker, "side": side,
            "qty": actual_qty,
            "dollar_amount": dollar_amount, "mode": mode,
            "timestamp": datetime.now().isoformat(), "reason": reason,
        }
        try:
            import db
            if db.db_available(): db.save_trade(result)
        except Exception:
            pass
        return result
    except Exception as e:
        return {"status": "error", "reason": str(e), "ticker": ticker}


def get_positions() -> list[dict]:
    """Return open positions with SL/TP info from active orders.

    CRITICAL: must fetch HELD orders too — bracket stop/TP children sit in
    'held' status. Filtering by OPEN only misses them and the dashboard
    falls back to fake calculated values (entry × 0.97).
    """
    if not is_configured():
        return []
    try:
        client    = _get_client()
        positions = client.get_all_positions()
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        # Get ALL active orders (open + held + new + accepted)
        _all = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, limit=400))
        orders = [o for o in _all if is_active_order(o)]
        sl_tp_map    = {}   # ticker → {stop_loss, take_profit}
        trailing_set = set()  # tickers with an active native trailing stop
        for o in orders:
            sym   = o.symbol
            otype = str(getattr(o, "type", "")).lower()
            # After bracket fills, child orders appear as standalone open orders:
            # TP leg → OrderType.LIMIT  (limit_price set)
            # SL leg → OrderType.STOP   (stop_price set)
            if "limit" in otype and "stop" not in otype:
                lp = getattr(o, "limit_price", None)
                if lp:
                    sl_tp_map.setdefault(sym, {})["take_profit"] = float(lp)
            if "trailing" in otype:
                # Native trailing stop — use live calculated stop_price as the SL
                sp = getattr(o, "stop_price", None)
                if sp:
                    sl_tp_map.setdefault(sym, {})["stop_loss"] = float(sp)
                trailing_set.add(sym)
            elif "stop" in otype:
                sp = getattr(o, "stop_price", None)
                if sp:
                    sl_tp_map.setdefault(sym, {})["stop_loss"] = float(sp)
            # Also check legs (for unfilled bracket parent orders)
            for leg in (getattr(o, "legs", None) or []):
                if getattr(leg, "stop_price", None):
                    sl_tp_map.setdefault(sym, {})["stop_loss"] = float(leg.stop_price)
                if getattr(leg, "limit_price", None):
                    sl_tp_map.setdefault(sym, {})["take_profit"] = float(leg.limit_price)

        result = []
        for p in positions:
            entry = float(p.avg_entry_price)
            sym   = p.symbol
            known = sl_tp_map.get(sym, {})
            # H-2 fix: track whether SL/TP came from the broker or was COMPUTED
            # as a fallback. Dashboard / EOD report should render "computed"
            # differently so users don't see a fake number labelled as a real stop.
            is_short = "short" in str(getattr(p, "side", "")).lower()
            sl_from_broker = "stop_loss"   in known
            tp_from_broker = "take_profit" in known
            if is_short:
                sl = known.get("stop_loss")   or round(entry * (1 + KELLY_LOSS_PCT), 2)
                tp = known.get("take_profit") or round(entry * (1 - MOVE_TARGET_PCT), 2)
            else:
                sl = known.get("stop_loss")   or round(entry * (1 - KELLY_LOSS_PCT), 2)
                tp = known.get("take_profit") or round(entry * (1 + MOVE_TARGET_PCT), 2)
            result.append({
                "ticker":            sym,
                "qty":               float(p.qty),
                "market_value":      float(p.market_value),
                "unrealized_pl":     float(p.unrealized_pl),
                "unrealized_pl_pct": float(p.unrealized_plpc) * 100,
                "side":              str(p.side),
                "avg_entry_price":   entry,
                "current_price":     float(p.current_price),
                "stop_loss":         sl,
                "take_profit":       tp,
                "stop_loss_source":  "broker" if sl_from_broker else "computed",
                "take_profit_source":"broker" if tp_from_broker else "computed",
                "is_trailing":       sym in trailing_set,
            })
        return result
    except Exception as e:
        print(f"[APEX] get_positions error: {e}")
        return []


def get_closed_trade_pnl(days: int = 60) -> list[dict]:
    """
    Fetch realized P&L for ALL closed trades — bracket exits AND manual closes.

    Strategy: find all filled SELL orders, match each to its most recent BUY fill
    for the same ticker to compute entry → exit P&L.

    Returns list of dicts:
        ticker, side, qty, entry_price, exit_price, realized_pnl,
        realized_pnl_pct, outcome ('tp_hit'|'sl_hit'|'manual'), closed_at
    """
    if not is_configured():
        return []
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        from datetime import datetime, timedelta

        client = _get_client()
        after  = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

        all_orders = client.get_orders(GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            after=after,
            limit=500,
        ))

        # Keep only filled orders with a fill price
        filled = [o for o in all_orders
                  if o.filled_avg_price and o.filled_qty
                  and float(o.filled_qty) > 0 and o.filled_at]

        # Group by ticker
        by_ticker: dict = {}
        for o in filled:
            by_ticker.setdefault(o.symbol, []).append(o)

        # ── FIFO matching — same accounting method Alpaca uses ───────────────
        # Walks fills in chronological order, tracking remaining qty per entry.
        # An exit consumes entries from the oldest-first; if exit qty > oldest
        # entry remaining, it spills to the next entry. Each share is matched
        # exactly once → no double-counting, no inflated P&L.
        results = []
        for ticker, orders in by_ticker.items():
            # Sort all fills chronologically (mix of buy + sell)
            fills = sorted(orders, key=lambda o: o.filled_at)

            # Open lots: list of dicts tracking remaining shares per entry
            # For longs: lots have side="long", positive qty (opened by buy)
            # For shorts: lots have side="short", positive qty (opened by sell)
            open_lots: list = []

            for fill in fills:
                fill_side = str(fill.side).lower()
                fill_qty  = float(fill.filled_qty)
                fill_px   = float(fill.filled_avg_price)
                fill_type = str(getattr(fill, "type", "")).lower()
                fill_time = str(fill.filled_at)[:16].replace("T", " ")
                is_buy    = "buy" in fill_side

                # Determine if this fill OPENS or CLOSES a lot.
                # Default rule: BUY opens long, SELL opens short — UNLESS
                # there's an opposing open lot, in which case it closes.
                if is_buy:
                    # BUY closes any open SHORT lots first (FIFO cover)
                    short_lots = [l for l in open_lots if l["side"] == "short"]
                    if short_lots:
                        qty_to_close = fill_qty
                        while qty_to_close > 0 and short_lots:
                            lot = short_lots[0]
                            matched = min(qty_to_close, lot["qty"])
                            pnl = round((lot["price"] - fill_px) * matched, 2)
                            pnl_pct = round((lot["price"] / fill_px - 1) * 100, 2) if fill_px else 0
                            outcome = ("tp_hit" if "limit" in fill_type and pnl > 0
                                       else "sl_hit" if "stop" in fill_type and pnl < 0
                                       else "manual")
                            results.append({
                                "ticker": ticker, "side": "short", "qty": matched,
                                "entry_price": round(lot["price"], 2),
                                "exit_price":  round(fill_px, 2),
                                "realized_pnl": pnl, "realized_pnl_pct": pnl_pct,
                                "outcome": outcome, "closed_at": fill_time,
                            })
                            lot["qty"] -= matched
                            qty_to_close -= matched
                            if lot["qty"] <= 1e-9:
                                open_lots.remove(lot)
                                short_lots = [l for l in open_lots if l["side"] == "short"]
                        # Any remaining buy qty opens a new LONG lot
                        if qty_to_close > 1e-9:
                            open_lots.append({"side": "long", "price": fill_px, "qty": qty_to_close, "time": fill_time})
                    else:
                        # No shorts to close → open a long lot
                        open_lots.append({"side": "long", "price": fill_px, "qty": fill_qty, "time": fill_time})
                else:
                    # SELL closes any open LONG lots first (FIFO)
                    long_lots = [l for l in open_lots if l["side"] == "long"]
                    if long_lots:
                        qty_to_close = fill_qty
                        while qty_to_close > 0 and long_lots:
                            lot = long_lots[0]
                            matched = min(qty_to_close, lot["qty"])
                            pnl = round((fill_px - lot["price"]) * matched, 2)
                            pnl_pct = round((fill_px / lot["price"] - 1) * 100, 2) if lot["price"] else 0
                            outcome = ("tp_hit" if "limit" in fill_type and pnl > 0
                                       else "sl_hit" if "stop" in fill_type and pnl < 0
                                       else "manual")
                            results.append({
                                "ticker": ticker, "side": "long", "qty": matched,
                                "entry_price": round(lot["price"], 2),
                                "exit_price":  round(fill_px, 2),
                                "realized_pnl": pnl, "realized_pnl_pct": pnl_pct,
                                "outcome": outcome, "closed_at": fill_time,
                            })
                            lot["qty"] -= matched
                            qty_to_close -= matched
                            if lot["qty"] <= 1e-9:
                                open_lots.remove(lot)
                                long_lots = [l for l in open_lots if l["side"] == "long"]
                        # Any remaining sell qty opens a new SHORT lot
                        if qty_to_close > 1e-9:
                            open_lots.append({"side": "short", "price": fill_px, "qty": qty_to_close, "time": fill_time})
                    else:
                        # No longs to close → open a short lot
                        open_lots.append({"side": "short", "price": fill_px, "qty": fill_qty, "time": fill_time})

        return sorted(results, key=lambda x: x["closed_at"], reverse=True)

    except Exception as e:
        print(f"[APEX] get_closed_trade_pnl error: {e}")
        return []


def close_position(ticker: str) -> dict:
    """
    Close an open position immediately at market price.

    Must cancel BOTH open and held orders before closing — bracket stop/TP
    children sit in 'held' status and hold the position's shares hostage.
    Without cancelling those, close_position() fails with 'insufficient qty'.
    """
    if not is_configured():
        return {"status": "skipped"}
    try:
        import time as _time
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        client = _get_client()

        # Cancel ALL active orders for this ticker (open + held + new + accepted)
        try:
            all_orders = client.get_orders(GetOrdersRequest(
                status=QueryOrderStatus.ALL, limit=400))
            cancelled = 0
            for o in all_orders:
                if o.symbol != ticker:
                    continue
                if not is_active_order(o):
                    continue
                try:
                    client.cancel_order_by_id(str(o.id))
                    cancelled += 1
                except Exception:
                    pass
            # Give Alpaca a moment to release the held shares
            if cancelled:
                _time.sleep(0.5)
        except Exception as _ce:
            # M-2 fix: if the WHOLE cancel-loop fails (Alpaca API down, auth
            # broken), proceed-to-close at line 730 will also fail confusingly.
            # One log line tells us why.
            print(f"[close_position] {ticker} pre-cancel loop failed: {_ce}")

        # Close the position — retry once with a longer wait if first attempt fails
        try:
            client.close_position(ticker)
        except Exception as first_err:
            if "insufficient" in str(first_err).lower() or "held" in str(first_err).lower():
                _time.sleep(1.5)
                client.close_position(ticker)
            else:
                raise

        # R-4 fix: write a status="closed" row so get_partial_exit_history()'s
        # last_close lookup actually works. Without this row, partial-exit
        # entries from a CLOSED prior position could leak into a future re-entry.
        try:
            import db as _db
            if _db.db_available():
                _db.save_trade({
                    "order_id":  f"close-{ticker}-{int(_time.time())}",
                    "ticker":    ticker,
                    "side":      "close",
                    "dollar_amount": 0,
                    "mode":      "LIVE" if is_live_mode() else "PAPER",
                    "status":    "closed",
                    "reason":    "close_position() called",
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception as _ce:
            print(f"[close_position] could not log close to DB: {_ce}")

        return {"status": "closed", "ticker": ticker, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "error", "reason": str(e), "ticker": ticker}


def tighten_stop(ticker: str, stop_pct: float = 0.015) -> dict:
    """
    Cancel existing stop loss for ticker and replace with a tighter one.
    stop_pct: how far below current price to set the new stop (default 1.5%).
    Used by sentiment_guard when a position's sentiment turns negative.
    """
    if not is_configured():
        return {"status": "skipped"}
    try:
        from alpaca.trading.requests import (GetOrdersRequest, StopOrderRequest)
        from alpaca.trading.enums import (QueryOrderStatus, OrderSide, TimeInForce)

        client = _get_client()

        # Get current price
        price = get_current_price(ticker)
        if not price:
            return {"status": "error", "reason": "Could not fetch price"}

        # Cancel existing stop orders for this ticker.
        # CRITICAL audit C-2: Bracket SL legs sit in HELD (not OPEN). Querying
        # OPEN-only meant tighten_stop() stacked a new tighter stop ON TOP of
        # the old wider one — could result in duplicate exits or naked qty.
        active_orders = [o for o in client.get_orders(GetOrdersRequest(
                            status=QueryOrderStatus.ALL, limit=500))
                         if is_active_order(o)]
        cancelled = 0
        qty = 0
        for o in active_orders:
            if o.symbol != ticker:
                continue
            otype = str(getattr(o, "type", "")).lower()
            if "stop" in otype and "limit" not in otype and "trailing" not in otype:
                try:
                    client.cancel_order_by_id(str(o.id))
                    cancelled += 1
                    if not qty and o.qty:
                        qty = float(o.qty)
                except Exception:
                    pass

        if not qty:
            # Try to get qty from position
            positions = get_positions()
            for p in positions:
                if p["ticker"] == ticker:
                    qty = p["qty"]
                    break

        if not qty:
            return {"status": "error", "reason": "Could not determine qty"}

        # Determine if position is long or short to set correct stop side
        positions_now = get_positions()
        is_short = False
        for pos in positions_now:
            if pos["ticker"] == ticker:
                is_short = "short" in str(pos.get("side", "")).lower()
                break

        # For longs:  stop is below current price (sell to exit)
        # For shorts: stop is above current price (buy to exit)
        if is_short:
            new_stop = round(price * (1 + stop_pct), 2)
            stop_side = OrderSide.BUY
        else:
            new_stop = round(price * (1 - stop_pct), 2)
            stop_side = OrderSide.SELL

        from alpaca.trading.requests import MarketOrderRequest
        stop_req = StopOrderRequest(
            symbol        = ticker,
            qty           = qty,
            side          = stop_side,
            time_in_force = TimeInForce.GTC,
            stop_price    = new_stop,
        )
        order = client.submit_order(stop_req)
        mode  = "LIVE" if is_live_mode() else "PAPER"
        print(f"[VIGIL] [{mode}] {ticker} stop tightened → ${new_stop:.2f} "
              f"({stop_pct*100:.1f}% below ${price:.2f})")
        return {
            "status":    "tightened",
            "ticker":    ticker,
            "new_stop":  new_stop,
            "price":     price,
            "stop_pct":  stop_pct,
            "order_id":  str(order.id),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e), "ticker": ticker}


def trail_positions(
    trigger_pct: float | None = None,
    trail_pct:   float | None = None,
) -> list[dict]:
    """
    Trailing stop manager — call every 30 min during market hours.

    For every LONG position that is up ≥ trigger_pct:
      1. Cancel the existing fixed stop-loss order (if still open)
      2. Leave the take-profit limit order untouched
      3. Place an Alpaca native trailing stop (GTC) at trail_pct below peak

    Partial exit (two-tier scale-out) — if ENABLE_PARTIAL_EXIT is True:
      Tier 1 at +7%:  close 33% of original, move stop to breakeven
      Tier 2 at +12%: close another 33% (same qty as T1, = 33% of original)
      Remaining 34%:  rides with AEGIS trailing stop
      Each tier logged to Supabase so it never fires twice per position.

    Already-trailing positions are detected by order type and skipped,
    so this is safe to call repeatedly.

    Returns a list of dicts for positions that were upgraded to trailing.
    """
    from config import (TRAIL_TRIGGER_PCT, TRAIL_PCT, TRAIL_TIGHTEN_LEVELS,
                        ENABLE_PARTIAL_EXIT, PARTIAL_EXIT_MOVE_TO_BE,
                        PARTIAL_EXIT_TIER1_TRIGGER, PARTIAL_EXIT_TIER1_FRACTION,
                        PARTIAL_EXIT_TIER2_TRIGGER, PARTIAL_EXIT_TIER2_FRACTION)

    trigger = trigger_pct if trigger_pct is not None else TRAIL_TRIGGER_PCT
    trail   = trail_pct   if trail_pct   is not None else TRAIL_PCT

    def _target_trail(pct_gain_decimal: float) -> float:
        """Return the tightest applicable trail % for this gain level."""
        for min_gain, t_pct in TRAIL_TIGHTEN_LEVELS:
            if pct_gain_decimal >= min_gain:
                return t_pct
        return trail

    if not is_configured():
        return []

    if not is_configured():
        pass  # is_configured() check already at line 821 — defensive
    results = []
    try:
        from alpaca.trading.requests import (GetOrdersRequest,
                                              TrailingStopOrderRequest,
                                              MarketOrderRequest,
                                              StopOrderRequest)
        from alpaca.trading.enums import (QueryOrderStatus, OrderSide,
                                          TimeInForce)

        client    = _get_client()
        positions = get_positions()
        if not positions:
            return []

        # CRITICAL audit C-6: load partial-exit history filtered to currently-
        # open tickers ONLY. Otherwise a stale t1/t2 record from a CLOSED prior
        # position in the same ticker makes the new position skip its scale-out.
        _open_tickers = {p["ticker"] for p in positions}
        partial_history: dict = {}
        if ENABLE_PARTIAL_EXIT:
            try:
                from db import get_partial_exit_history
                partial_history = get_partial_exit_history(open_tickers=_open_tickers)
            except Exception as _dbe:
                print(f"[AEGIS] Could not load partial exit history: {_dbe}")

        # Build map: ticker → active order list
        # Must include HELD orders — bracket stop/TP children are held, not open.
        # Without held orders, AEGIS can't see or cancel bracket stops.
        from alpaca.trading.enums import QueryOrderStatus as _QOS
        _all_active = client.get_orders(
            GetOrdersRequest(status=_QOS.ALL, limit=400))
        open_orders = [o for o in _all_active if is_active_order(o)]
        orders_by_ticker: dict = {}
        for o in open_orders:
            orders_by_ticker.setdefault(o.symbol, []).append(o)

        # Load penny-stock floor — rule: no positions below MIN_STOCK_PRICE
        try:
            from config import MIN_STOCK_PRICE as _MIN_PRICE
        except Exception:
            _MIN_PRICE = 5.0

        for p in positions:
            ticker   = p["ticker"]
            pct_gain = p.get("unrealized_pl_pct", 0)  # already in %
            qty      = abs(float(p["qty"]))  # shorts come through as negative
            raw_side = str(p.get("side", "")).lower()
            is_long  = "long" in raw_side or "buy" in raw_side
            cur_px   = float(p.get("current_price", 0) or 0)

            ticker_orders = orders_by_ticker.get(ticker, [])
            pct_gain_decimal = pct_gain / 100.0

            # ══════════════════════════════════════════════════════════════════
            # RULE: no penny stocks. If a position drifted below MIN_STOCK_PRICE,
            # close it at market — wide spreads + thin liquidity are killers.
            # Runs FIRST so we don't waste an AEGIS cycle placing stops on a
            # position we're about to close anyway.
            # ══════════════════════════════════════════════════════════════════
            if cur_px > 0 and cur_px < _MIN_PRICE:
                try:
                    print(f"[AEGIS] {ticker} below ${_MIN_PRICE} floor (cur ${cur_px:.2f}) — auto-closing")
                    _close_result = close_position(ticker)
                    results.append({
                        "ticker": ticker, "pct_gain": round(pct_gain, 2),
                        "trail_pct": 0, "order_id": "n/a",
                        "cancelled_sl": 0, "status": "closed_penny_stock",
                        "timestamp": datetime.now().isoformat(),
                    })
                    try:
                        from alerts.slack import _post
                        _post({"text": (
                            f"🪙 *Penny-stock auto-close — {ticker}*\n"
                            f">{('LONG' if is_long else 'SHORT')} {qty:g} @ ${cur_px:.2f} "
                            f"(below ${_MIN_PRICE:.2f} floor) · P&L {pct_gain:+.1f}%"
                        )})
                    except Exception:
                        pass
                except Exception as _ce:
                    print(f"[AEGIS] {ticker} penny-close FAILED: {_ce}")
                continue   # skip stop / trailing logic — position is closing

            # ══════════════════════════════════════════════════════════════════
            # RULE: every position MUST have a stop, ALWAYS.
            # Runs BEFORE partial-exit / trailing logic so naked LOSING positions
            # get rescued too (those don't qualify for any other branch).
            # ══════════════════════════════════════════════════════════════════
            _has_stop = any(
                "stop" in str(getattr(o, "type", "")).lower()
                for o in ticker_orders
            )
            if not _has_stop:
                _entry_px = float(p.get("avg_entry_price", 0) or 0)
                _cur_px   = float(p.get("current_price", _entry_px))
                if _entry_px > 0 and _cur_px > 0 and qty > 0:
                    # Constraint:
                    #   LONG  → stop MUST be BELOW current price
                    #   SHORT → stop MUST be ABOVE current price
                    # For positions still in profit (or near entry), use the
                    # tighter of (entry-based 3% risk) and (current ±3%).
                    # For positions already underwater past the entry stop,
                    # the entry-based stop is invalid (wrong side of current);
                    # cap loss from CURRENT price instead.
                    if is_long:
                        risk_stop = round(_entry_px * (1 - KELLY_LOSS_PCT), 2)
                        cur_stop  = round(_cur_px   * (1 - KELLY_LOSS_PCT), 2)
                        if risk_stop < _cur_px:
                            # Entry-based stop still valid — use tighter of the two
                            new_stop = max(risk_stop, cur_stop)
                        else:
                            # Already underwater past entry stop → cap from current
                            new_stop = cur_stop
                        stop_side = OrderSide.SELL
                    else:
                        risk_stop = round(_entry_px * (1 + KELLY_LOSS_PCT), 2)
                        cur_stop  = round(_cur_px   * (1 + KELLY_LOSS_PCT), 2)
                        if risk_stop > _cur_px:
                            new_stop = min(risk_stop, cur_stop)
                        else:
                            new_stop = cur_stop
                        stop_side = OrderSide.BUY
                    # H-8 fix: Alpaca rejects fractional-qty stop orders. For
                    # fractional positions, use whole-share qty (floor) for the
                    # stop; the fractional dust is unprotected but small enough
                    # that the dollar risk is acceptable, and at least the bulk
                    # of the position gets covered (previously it stayed fully
                    # naked forever because every retry failed).
                    import math as _math
                    _is_fractional = qty != int(qty)
                    _stop_qty = int(_math.floor(qty)) if _is_fractional else qty
                    if _stop_qty <= 0:
                        # Pure-fractional (e.g. 0.7 BTC) — close instead of stop
                        try:
                            print(f"[AEGIS] {ticker} pure-fractional naked → close_position")
                            close_position(ticker)
                        except Exception as _cf:
                            print(f"[AEGIS] {ticker} fractional close failed: {_cf}")
                        continue
                    try:
                        from alpaca.trading.requests import StopOrderRequest as _SOR
                        _rescue_req = _SOR(
                            symbol=ticker, qty=_stop_qty, side=stop_side,
                            stop_price=new_stop, time_in_force=TimeInForce.GTC,
                        )
                        try:
                            _rescue_ord = client.submit_order(_rescue_req)
                        except Exception:
                            _rescue_req.time_in_force = TimeInForce.DAY
                            _rescue_ord = client.submit_order(_rescue_req)
                        _frac_note = f" (fractional dust {qty - _stop_qty:.4f} uncovered)" if _is_fractional else ""
                        print(f"[AEGIS] {ticker} was NAKED — placed rescue stop @ ${new_stop:.2f}{_frac_note}")
                        results.append({
                            "ticker": ticker, "pct_gain": round(pct_gain, 2),
                            "trail_pct": KELLY_LOSS_PCT, "order_id": str(_rescue_ord.id),
                            "cancelled_sl": 0, "status": "rescue_stop_placed",
                            "timestamp": datetime.now().isoformat(),
                        })
                        # Slack ping — naked positions are a safety incident.
                        # N-7 fix: dedup per ticker per day so a stuck naked
                        # position doesn't fire 32 Slack messages/day (one
                        # per 15-min AEGIS run).
                        try:
                            import db as _db
                            _send = True
                            if _db.db_available():
                                from datetime import datetime as _dt, timedelta as _td
                                _cutoff = (_dt.utcnow() - _td(hours=8)).isoformat()
                                _hits = (_db._client().table("trades")
                                            .select("timestamp")
                                            .eq("status", f"aegis_rescue_alert:{ticker}")
                                            .gte("timestamp", _cutoff)
                                            .limit(1).execute())
                                if _hits.data:
                                    _send = False
                                else:
                                    _db.save_trade({
                                        "order_id": f"aegis-alert-{ticker}-{int(datetime.now().timestamp())}",
                                        "ticker": ticker, "side": "alert", "dollar_amount": 0,
                                        "mode": "LIVE" if is_live_mode() else "PAPER",
                                        "status": f"aegis_rescue_alert:{ticker}",
                                        "reason": "naked_rescue", "timestamp": datetime.now().isoformat(),
                                    })
                            if _send:
                                from alerts.slack import _post
                                _post({"text": (
                                    f"🩹 *Naked position rescued — {ticker}*\n"
                                    f">{('LONG' if is_long else 'SHORT')} {qty:g} @ avg ${_entry_px:.2f} · "
                                    f"current ${_cur_px:.2f} · P&L {pct_gain:+.1f}%\n"
                                    f">Placed rescue stop @ ${new_stop:.2f} "
                                    f"({KELLY_LOSS_PCT*100:.0f}% risk cap from "
                                    f"{'entry' if new_stop == risk_stop else 'current price'})\n"
                                    f">_Further rescue alerts for {ticker} silenced for 8h_"
                                )})
                        except Exception:
                            pass
                        # Re-fetch this ticker's orders so subsequent logic sees the rescue stop
                        ticker_orders = ticker_orders + [_rescue_ord]
                    except Exception as _re:
                        print(f"[AEGIS] {ticker} naked-rescue FAILED: {_re}")
                        # Even louder Slack — couldn't place a stop, requires human
                        try:
                            from alerts.slack import _post
                            _post({"text": (
                                f"🚨 *NAKED POSITION — could not place stop: {ticker}*\n"
                                f">{('LONG' if is_long else 'SHORT')} {qty:g} @ ${_entry_px:.2f}\n"
                                f">Error: {str(_re)[:200]}\n"
                                f">*Action required:* manually place a stop or close the position."
                            )})
                        except Exception:
                            pass
            # ══════════════════════════════════════════════════════════════════

            # ── Two-tier partial exit (scale-out) ─────────────────────────────
            # Tier 1 at +7%:  close 33% of ORIGINAL, move stop to breakeven
            # Tier 2 at +12%: close another 33% (= same qty as T1, so 66% closed)
            # Remaining 34%:  rides with multi-level trailing stop
            if ENABLE_PARTIAL_EXIT:
                _hist = partial_history.get(ticker, {"t1": False, "t2": False, "t1_qty": 0.0})
                _abs_qty   = abs(float(qty))
                _entry_px  = float(p.get("avg_entry_price", 0))
                _current_px = float(p.get("current_price", 0))

                def _fire_tier(tier_name: str, fraction_to_close: float,
                               trigger_pct: float, move_to_be: bool):
                    """Inner helper — fire one partial exit tier."""
                    nonlocal _abs_qty
                    import math as _math

                    # qty to close = 33% of ORIGINAL position
                    if tier_name == "t1":
                        raw_qty = _abs_qty * fraction_to_close
                    else:
                        raw_qty = _hist.get("t1_qty", 0) or (_abs_qty * fraction_to_close)
                        raw_qty = min(raw_qty, _abs_qty)

                    # ALWAYS floor to whole shares — cleaner orders, no Alpaca
                    # complaints on non-fractionable assets, no weird .05 / .79
                    # share displays in Slack alerts. The dropped fractional part
                    # rides with the trailing stop alongside the remaining 34%.
                    close_qty  = int(_math.floor(raw_qty))
                    if close_qty <= 0:
                        return None
                    # Remaining can still be fractional if the position was opened
                    # that way (fractional buy) — that's fine for the stop order.
                    remain_qty = round(_abs_qty - close_qty, 4)
                    exit_side  = OrderSide.SELL if is_long else OrderSide.BUY

                    # ── Snapshot existing stops AND bracket TP legs BEFORE
                    # cancelling. Restore on failure. CRITICAL audit C-7: was
                    # only cancelling stops — the bracket's LIMIT TP leg was
                    # left at original qty, so when remaining tranche hits TP
                    # it tries to sell MORE shares than held → Alpaca rejects
                    # → uncovered position.
                    _stop_snapshots = []
                    _tp_snapshots   = []
                    for o in ticker_orders:
                        otype = str(getattr(o, "type", "")).lower()
                        if not is_active_order(o):
                            continue
                        if "stop" in otype:
                            _stop_snapshots.append({
                                "type":  otype,
                                "qty":   float(o.qty) if o.qty else _abs_qty,
                                "side":  o.side,
                                "stop_price":    float(o.stop_price) if o.stop_price else None,
                                "trail_percent": float(getattr(o, "trail_percent", 0) or 0),
                            })
                            try:
                                client.cancel_order_by_id(str(o.id))
                            except Exception:
                                pass
                        elif otype == "limit" and getattr(o, "parent_order_id", None):
                            # Bracket TP leg — also needs resize after partial
                            _tp_snapshots.append({
                                "qty":         float(o.qty) if o.qty else _abs_qty,
                                "side":        o.side,
                                "limit_price": float(o.limit_price) if o.limit_price else None,
                            })
                            try:
                                client.cancel_order_by_id(str(o.id))
                            except Exception:
                                pass

                    # Market-close the tier qty — if it fails, RESTORE the stop
                    mreq = MarketOrderRequest(
                        symbol=ticker, qty=close_qty, side=exit_side,
                        time_in_force=TimeInForce.DAY,
                    )
                    try:
                        close_order = client.submit_order(mreq)
                    except Exception as _sell_err:
                        # CRITICAL: restore the stops AND TP we just cancelled.
                        # H-9 fix: restore trailing stops as TrailingStopOrderRequest
                        # NEVER as a fixed StopOrderRequest with snapshotted price —
                        # snapshot captured peak-derived stop_price which is now stale.
                        for _snap in _stop_snapshots:
                            try:
                                if "trailing" in _snap["type"] and _snap["trail_percent"]:
                                    from alpaca.trading.requests import TrailingStopOrderRequest as _TSR
                                    _restore = _TSR(
                                        symbol=ticker, qty=_snap["qty"], side=_snap["side"],
                                        time_in_force=TimeInForce.GTC,
                                        trail_percent=_snap["trail_percent"],
                                    )
                                elif "trailing" in _snap["type"]:
                                    # Trailing but no trail_percent snapshot — skip
                                    # rather than degrade to a stale fixed stop.
                                    print(f"[AEGIS] {ticker} skipped trailing restore (no trail_percent)")
                                    continue
                                else:
                                    _restore = StopOrderRequest(
                                        symbol=ticker, qty=_snap["qty"], side=_snap["side"],
                                        stop_price=_snap["stop_price"],
                                        time_in_force=TimeInForce.GTC,
                                    )
                                client.submit_order(_restore)
                            except Exception:
                                try:
                                    _restore.time_in_force = TimeInForce.DAY
                                    client.submit_order(_restore)
                                except Exception:
                                    pass
                        # Also restore TP legs at ORIGINAL qty (sell didn't happen)
                        for _tp in _tp_snapshots:
                            try:
                                from alpaca.trading.requests import LimitOrderRequest as _LOR
                                _tpr = _LOR(symbol=ticker, qty=_tp["qty"], side=_tp["side"],
                                            limit_price=_tp["limit_price"],
                                            time_in_force=TimeInForce.GTC)
                                client.submit_order(_tpr)
                            except Exception:
                                pass
                        print(f"[AEGIS] {ticker} {tier_name} sell failed: {_sell_err} — restored stops+TP")
                        raise

                    # T1 moves remaining stop to breakeven
                    # T2 leaves stop at breakeven (already there from T1)
                    # CRITICAL: after a successful partial sell, we MUST place a stop.
                    # If the ideal stop (breakeven) fails, fall back to any stop below
                    # current price — naked is never acceptable after a sell.
                    if remain_qty > 0 and _entry_px > 0:
                        be_side = OrderSide.SELL if is_long else OrderSide.BUY
                        # Try ideal stop (breakeven if move_to_be, else use current-3%)
                        _stop_px = round(_entry_px, 2) if move_to_be else round(
                            (_current_px * 0.97 if is_long else _current_px * 1.03), 2)
                        _stop_placed = False
                        for _tif in [TimeInForce.GTC, TimeInForce.DAY]:
                            try:
                                client.submit_order(StopOrderRequest(
                                    symbol=ticker, qty=remain_qty, side=be_side,
                                    stop_price=_stop_px, time_in_force=_tif))
                                _stop_placed = True
                                break
                            except Exception:
                                pass
                        if not _stop_placed:
                            # Last-resort: place stop 3% below/above current — anything > naked
                            _fallback_px = round((_current_px * 0.97 if is_long else _current_px * 1.03), 2)
                            try:
                                client.submit_order(StopOrderRequest(
                                    symbol=ticker, qty=remain_qty, side=be_side,
                                    stop_price=_fallback_px, time_in_force=TimeInForce.DAY))
                                _stop_placed = True
                                print(f"[AEGIS] {ticker} {tier_name}: breakeven stop failed — placed fallback stop @ ${_fallback_px:.2f}")
                            except Exception as _se:
                                print(f"[AEGIS] {ticker} {tier_name}: ALL stop placements failed: {_se}")
                        if not _stop_placed:
                            # Genuinely naked after partial sell — fire Slack alert
                            try:
                                from alerts.slack import _post
                                _post({"text": (
                                    f"🚨 *NAKED after partial exit — {ticker}*\n"
                                    f">Sold {close_qty} shares but FAILED to place replacement stop\n"
                                    f">Remaining: {remain_qty} shares · *Manual stop required NOW*"
                                )})
                            except Exception:
                                pass

                    # CRITICAL audit C-7: reissue bracket TP sized to remain_qty.
                    # Was leaving orphan TP at original qty → would over-sell on
                    # exit and Alpaca would reject → no TP coverage on the tranche.
                    # R-2 fix: reissue TP sized to remain_qty. If broker had a
                    # bracket TP, reuse its limit price. If not (position came
                    # from _place_simple_order / naked rescue / sentiment_guard
                    # replacement / crypto), synthesize one at MOVE_TARGET_PCT
                    # from entry — otherwise the tranche has NO upside exit at all.
                    if remain_qty > 0:
                        try:
                            from alpaca.trading.requests import LimitOrderRequest as _LOR
                            from config import MOVE_TARGET_PCT as _MTP
                            if _tp_snapshots:
                                _tp0 = _tp_snapshots[0]
                                _tp_side, _tp_px = _tp0["side"], _tp0["limit_price"]
                                _src = "broker"
                            else:
                                _tp_side = OrderSide.SELL if is_long else OrderSide.BUY
                                _tp_px = (round(_entry_px * (1 + _MTP), 2)
                                          if is_long else
                                          round(_entry_px * (1 - _MTP), 2))
                                _src = "synthesized"
                            _tp_req = _LOR(
                                symbol=ticker, qty=remain_qty, side=_tp_side,
                                limit_price=_tp_px,
                                time_in_force=TimeInForce.GTC,
                            )
                            client.submit_order(_tp_req)
                            print(f"[AEGIS] {ticker} TP ({_src}) sized to {remain_qty} @ ${_tp_px:.2f}")
                        except Exception as _tpe:
                            print(f"[AEGIS] {ticker} could not reissue TP at remain_qty: {_tpe}")

                    # Log to Supabase — status encodes which tier fired
                    try:
                        from db import save_trade
                        save_trade({
                            "order_id":     str(close_order.id),
                            "ticker":       ticker,
                            "side":         "sell_partial" if is_long else "buy_partial",
                            "dollar_amount": round(close_qty * _current_px, 2),
                            "mode":         "LIVE" if is_live_mode() else "PAPER",
                            "status":       f"partial_exit_{tier_name}",
                            "reason":       (f"Tier-{tier_name.upper()[1]} scale-out "
                                             f"{fraction_to_close*100:.0f}% at +{pct_gain:.1f}% "
                                             f"gain qty={close_qty}"),
                            "timestamp":    datetime.now().isoformat(),
                        })
                    except Exception as dbe:
                        print(f"[AEGIS] Could not log {tier_name} to DB: {dbe}")

                    pnl_locked = round(close_qty * (_current_px - _entry_px)
                                       * (1 if is_long else -1), 2)
                    mode_tag   = "LIVE" if is_live_mode() else "PAPER"
                    tier_lbl   = "T1" if tier_name == "t1" else "T2"
                    print(f"[AEGIS] [{mode_tag}] ✂️ PARTIAL EXIT {tier_lbl} {ticker}: "
                          f"closed {close_qty} shares at +{pct_gain:.1f}% "
                          f"(locked ${pnl_locked:+.2f}), remaining {remain_qty} shares")

                    try:
                        from alerts.slack import _post
                        be_note = f" · stop → breakeven (${_entry_px:.2f})" if move_to_be else ""
                        _post({"text": (
                            f"✂️ *Partial exit {tier_lbl} — {ticker}* (+{pct_gain:.1f}%)\n"
                            f">Closed *{fraction_to_close*100:.0f}%* "
                            f"({close_qty} shares) · locked in *${pnl_locked:+.2f}*\n"
                            f">Remaining *{remain_qty} shares*{be_note}"
                        )})
                    except Exception:
                        pass

                    _hist[tier_name] = True
                    if tier_name == "t1":
                        _hist["t1_qty"] = close_qty
                    partial_history[ticker] = _hist
                    _abs_qty = remain_qty  # update for any subsequent tier this run

                    return {
                        "ticker": ticker, "action": f"partial_exit_{tier_name}",
                        "pct_gain": round(pct_gain, 2), "qty_closed": close_qty,
                        "qty_remaining": remain_qty, "pnl_locked": pnl_locked,
                        "order_id": str(close_order.id),
                        "timestamp": datetime.now().isoformat(),
                    }

                fired_any = False
                # Tier 1
                if not _hist["t1"] and pct_gain_decimal >= PARTIAL_EXIT_TIER1_TRIGGER:
                    try:
                        r = _fire_tier("t1", PARTIAL_EXIT_TIER1_FRACTION,
                                       PARTIAL_EXIT_TIER1_TRIGGER,
                                       move_to_be=PARTIAL_EXIT_MOVE_TO_BE)
                        if r:
                            results.append(r)
                            fired_any = True
                    except Exception as e:
                        print(f"[AEGIS] Tier 1 exit failed for {ticker}: {e}")

                # Tier 2 — only check if T1 already fired AND gain ≥ 12%
                if (_hist["t1"] and not _hist["t2"]
                        and pct_gain_decimal >= PARTIAL_EXIT_TIER2_TRIGGER):
                    try:
                        r = _fire_tier("t2", PARTIAL_EXIT_TIER2_FRACTION,
                                       PARTIAL_EXIT_TIER2_TRIGGER,
                                       move_to_be=False)  # stop already at breakeven
                        if r:
                            results.append(r)
                            fired_any = True
                    except Exception as e:
                        print(f"[AEGIS] Tier 2 exit failed for {ticker}: {e}")

                if fired_any:
                    continue  # remaining qty gets trailing stop next AEGIS run
            # ── End partial exit ──────────────────────────────────────────────

            # Handle BOTH longs and shorts.
            # For a SHORT position that's profitable (price has gone DOWN),
            # the trailing stop is a BUY order (to cover) that trails DOWN
            # behind the price. Alpaca's TrailingStopOrderRequest figures
            # out the direction from the order side + trail_percent; we just
            # need to pass the right side (BUY to cover a short).
            trail_side = OrderSide.SELL if is_long else OrderSide.BUY

            # Not profitable enough yet for trailing stop
            if pct_gain < trigger * 100:
                continue

            target_trail = _target_trail(pct_gain_decimal)

            # Check for existing trailing stop
            existing_trail = next(
                (o for o in ticker_orders
                 if "trailing" in str(getattr(o, "type", "")).lower()),
                None
            )
            if existing_trail:
                # Already trailing — check if we need to tighten
                existing_pct = float(getattr(existing_trail, "trail_percent", 0) or 0)
                if existing_pct == 0 or target_trail >= existing_pct / 100:
                    # No tightening needed
                    print(f"[AEGIS] {ticker} trailing at {existing_pct:.1f}% — no tighten needed")
                    continue
                # Tighten: cancel old trailing stop, place tighter one
                try:
                    client.cancel_order_by_id(str(existing_trail.id))
                    print(f"[AEGIS] {ticker} tightening trail: {existing_pct:.1f}% → {target_trail*100:.1f}%")
                except Exception as _te:
                    # M-2 fix: was silent `continue`. If the same ticker fails
                    # to tighten over and over, we'd never see why.
                    print(f"[AEGIS] {ticker} trail-tighten cancel failed: {_te} — leaving existing trail in place")
                    continue  # if cancel fails, skip to avoid duplicates
            else:
                # No trailing stop — only activate if gain >= trigger
                if pct_gain < trigger * 100:
                    continue

            # Process each position in its own try/except so one failure
            # (e.g. fractional share DAY-only restriction) doesn't kill the loop
            try:
                # Cancel existing fixed stop-loss order(s).
                # Bracket child stops (HELD status) often can't be cancelled directly —
                # Alpaca requires cancelling the parent bracket order instead.
                # Strategy: try direct cancel first; on failure try parent; on failure
                # cancel ALL orders for this ticker (nuclear option — reissue TP after).
                cancelled = 0
                _tp_price_to_reissue = None  # track TP price in case we cancel the whole bracket
                for o in ticker_orders:
                    otype = str(getattr(o, "type", "")).lower()
                    if otype == "limit" and getattr(o, "parent_order_id", None):
                        # Capture bracket TP price so we can reissue it if the parent gets cancelled
                        if o.limit_price and not _tp_price_to_reissue:
                            _tp_price_to_reissue = float(o.limit_price)
                    if "stop" in otype and "limit" not in otype:
                        try:
                            client.cancel_order_by_id(str(o.id))
                            cancelled += 1
                            print(f"[AEGIS] {ticker} cancelled stop {str(o.id)[:8]} directly")
                        except Exception as _ce1:
                            # Direct cancel failed — try cancelling the parent bracket order
                            parent_id = getattr(o, "parent_order_id", None)
                            if parent_id:
                                try:
                                    client.cancel_order_by_id(str(parent_id))
                                    cancelled += 1
                                    print(f"[AEGIS] {ticker} cancelled parent bracket {str(parent_id)[:8]} (child was HELD)")
                                except Exception as _ce2:
                                    print(f"[AEGIS] {ticker} could not cancel stop or parent: {_ce1} / {_ce2}")
                            else:
                                print(f"[AEGIS] {ticker} could not cancel SL (no parent): {_ce1}")

                # Place native Alpaca trailing stop — try GTC first, DAY fallback for fractionals
                trail_pct_val = target_trail * 100   # Alpaca wants e.g. 3.0 for 3%
                assert 0.5 <= trail_pct_val <= 20, f"trail_percent {trail_pct_val} out of sane range"
                order = None
                for tif in [TimeInForce.GTC, TimeInForce.DAY]:
                    try:
                        trail_req = TrailingStopOrderRequest(
                            symbol        = ticker,
                            qty           = qty,
                            side          = trail_side,   # SELL for longs, BUY to cover shorts
                            time_in_force = tif,
                            trail_percent = trail_pct_val,
                        )
                        order = client.submit_order(trail_req)
                        break  # success
                    except Exception as oe:
                        if "fractional" in str(oe).lower() and tif == TimeInForce.GTC:
                            print(f"[AEGIS] {ticker} is fractional — retrying with DAY order")
                            continue
                        raise  # re-raise unexpected errors

                if order is None:
                    print(f"[AEGIS] {ticker}: could not place trailing stop — skipping")
                    continue

                mode = "LIVE" if is_live_mode() else "PAPER"
                print(f"[AEGIS] [{mode}] {ticker} up {pct_gain:.1f}% → "
                      f"trailing stop {trail*100:.0f}% activated "
                      f"(cancelled {cancelled} fixed SL)")

                result = {
                    "ticker":       ticker,
                    "pct_gain":     round(pct_gain, 2),
                    "trail_pct":    trail,
                    "order_id":     str(order.id),
                    "cancelled_sl": cancelled,
                    "status":       "trailing",
                    "timestamp":    datetime.now().isoformat(),
                }
                results.append(result)

                # Instant Slack ping
                try:
                    from alerts.slack import _post
                    _post({"text": (
                        f"🔒 *Trailing stop activated — {ticker}*\n"
                        f">Up *{pct_gain:.1f}%* · fixed SL replaced with "
                        f"*{trail*100:.0f}% trailing stop* below peak\n"
                        f">Take-profit target unchanged"
                    )})
                except Exception:
                    pass

            except Exception as e:
                # Alpaca won't allow trailing stops on fractional positions.
                # Simulate trailing: move the fixed stop to lock in profit.
                # For LONG  → stop is BELOW current, must be ABOVE entry
                # For SHORT → stop is ABOVE current, must be BELOW entry
                if "fractional" in str(e).lower():
                    _simulated = False
                    try:
                        current_price = p.get("current_price") or p.get("avg_entry_price", 0)
                        entry_px  = p.get("avg_entry_price", 0)
                        if is_long:
                            new_stop = round(current_price * (1 - trail), 2)
                            locks_profit = new_stop > entry_px
                        else:
                            new_stop = round(current_price * (1 + trail), 2)
                            locks_profit = new_stop < entry_px
                        if locks_profit:
                            # Cancel old stops
                            for o in ticker_orders:
                                otype = str(getattr(o, "type", "")).lower()
                                if "stop" in otype and "limit" not in otype and "trailing" not in otype:
                                    try:
                                        client.cancel_order_by_id(str(o.id))
                                    except Exception:
                                        pass
                            # Place new fixed stop that locks in profit
                            from alpaca.trading.requests import StopOrderRequest
                            stop_req = StopOrderRequest(
                                symbol        = ticker,
                                qty           = qty,
                                side          = trail_side,   # SELL for longs, BUY for shorts
                                time_in_force = TimeInForce.GTC,
                                stop_price    = new_stop,
                            )
                            try:
                                sord = client.submit_order(stop_req)
                            except Exception:
                                stop_req.time_in_force = TimeInForce.DAY
                                sord = client.submit_order(stop_req)
                            print(f"[AEGIS] {ticker} fractional — simulated trail: "
                                  f"stop moved to ${new_stop:.2f} (locks in profit)")
                            _simulated = True
                            results.append({
                                "ticker":       ticker,
                                "pct_gain":     round(pct_gain, 2),
                                "trail_pct":    trail,
                                "order_id":     str(sord.id),
                                "cancelled_sl": 0,
                                "status":       "simulated_trailing",
                                "timestamp":    datetime.now().isoformat(),
                            })
                    except Exception as se:
                        print(f"[AEGIS] {ticker} simulated trail failed: {se}")
                    if not _simulated:
                        print(f"[AEGIS] {ticker}: fractional, stop already above entry — no move needed")
                else:
                    print(f"[AEGIS] {ticker} trailing stop error: {e} — skipping")
                    try:
                        from alerts.slack import _post
                        _post({"text": (
                            f"⚠️ *AEGIS trailing stop FAILED — {ticker}*\n"
                            f">Position up *{pct_gain:.1f}%* but trailing stop could not be placed\n"
                            f">Error: `{str(e)[:200]}`\n"
                            f">*Action: check Alpaca dashboard — may need manual trailing stop*"
                        )})
                    except Exception:
                        pass

    except Exception as e:
        print(f"[AEGIS] trail_positions error: {e}")

    return results


def cancel_all_orders() -> int:
    """Cancel all active orders (open + new + held + accepted + pending_new).

    H-3 fix: was OPEN-only — bracket protective legs in HELD survived,
    causing orphan orders to accumulate after emergency cancel-all.
    """
    if not is_configured():
        return 0
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        client = _get_client()
        orders = [o for o in client.get_orders(GetOrdersRequest(
                       status=QueryOrderStatus.ALL, limit=500))
                  if is_active_order(o)]
        for o in orders:
            try:
                client.cancel_order_by_id(str(o.id))
            except Exception as _e:
                print(f"[cancel_all] {o.symbol} {o.id}: {_e}")
        return len(orders)
    except Exception as _e:
        print(f"[cancel_all] failed: {_e}")
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def place_crypto_order(alpaca_symbol: str, dollar_amount: float,
                       direction: str, reason: str = "",
                       execution_path: str = "") -> dict:
    """
    Place a crypto market order via Alpaca.

    - alpaca_symbol: Alpaca format e.g. "BTC/USD"
    - Crypto uses GTC (not DAY) — markets are 24/7
    - No bracket orders for crypto — places separate stop + limit orders after fill
    - Fractional crypto always supported (uses notional dollar amount)
    """
    from config import KELLY_LOSS_PCT, MOVE_TARGET_PCT
    if not is_configured():
        return {"status": "skipped", "reason": "Alpaca not configured"}

    # CRITICAL audit C-10: daily-loss kill switch also gates crypto.
    if not _check_daily_loss_limit():
        return {"status": "rejected_loss_limit",
                "reason": "Daily loss limit hit — crypto path also halted"}

    mode = "LIVE" if is_live_mode() else "PAPER"
    side = "buy" if direction in ("bullish", "long") else "sell"

    try:
        from alpaca.trading.requests import MarketOrderRequest, StopOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client    = _get_client()
        order_req = MarketOrderRequest(
            symbol        = alpaca_symbol,
            notional      = round(dollar_amount, 2),  # dollar-based for crypto
            side          = OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force = TimeInForce.GTC,          # crypto is 24/7
        )
        order = client.submit_order(order_req)
        print(f"[APEX] [{mode}] CRYPTO {side.upper()} ${dollar_amount:.0f} {alpaca_symbol}")

        # After submission, estimate price to set protective orders
        # (actual fill price may differ slightly)
        try:
            from alpaca.data.historical.crypto import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoLatestQuoteRequest
            dc    = CryptoHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            quote = dc.get_crypto_latest_quote(CryptoLatestQuoteRequest(symbol_or_symbols=alpaca_symbol))
            price = float(quote[alpaca_symbol].ask_price)
            qty   = dollar_amount / price

            if side == "buy":
                sl_price = round(price * (1 - KELLY_LOSS_PCT), 2)
                tp_price = round(price * (1 + MOVE_TARGET_PCT), 2)
                sl_side  = OrderSide.SELL
                tp_side  = OrderSide.SELL
            else:
                sl_price = round(price * (1 + KELLY_LOSS_PCT), 2)
                tp_price = round(price * (1 - MOVE_TARGET_PCT), 2)
                sl_side  = OrderSide.BUY
                tp_side  = OrderSide.BUY

            # Stop loss
            client.submit_order(StopOrderRequest(
                symbol=alpaca_symbol, notional=round(dollar_amount, 2),
                side=sl_side, time_in_force=TimeInForce.GTC, stop_price=sl_price))
            # Take profit
            client.submit_order(LimitOrderRequest(
                symbol=alpaca_symbol, notional=round(dollar_amount, 2),
                side=tp_side, time_in_force=TimeInForce.GTC, limit_price=tp_price))
            print(f"         SL: ${sl_price:.2f}  TP: ${tp_price:.2f}")
        except Exception as pe:
            print(f"[APEX] Crypto SL/TP placement failed: {pe} — position is unprotected")

        result = {
            "status":        "submitted",
            "order_id":      str(order.id),
            "ticker":        alpaca_symbol,
            "side":          side,
            "dollar_amount": dollar_amount,
            "asset_class":   "crypto",
            "mode":          mode,
            "timestamp":     datetime.now().isoformat(),
            "reason":        reason,
            "execution_path": execution_path,
        }
        try:
            import db
            if db.db_available():
                db.save_trade(result)
        except Exception:
            pass
        return result

    except Exception as e:
        print(f"[APEX] Crypto order failed for {alpaca_symbol}: {e}")
        return {"status": "error", "reason": str(e), "ticker": alpaca_symbol}


# ══════════════════════════════════════════════════════════════════════════════
# OPTIONS EXECUTION — IRON BUTTERFLY
# ══════════════════════════════════════════════════════════════════════════════

def place_iron_butterfly(ticker: str, expiry_yymmdd: str,
                         atm_strike: float, wing_width: float,
                         contracts: int = 1, reason: str = "") -> dict:
    """
    Place a short iron butterfly (credit strategy) via Alpaca multi-leg order.

    Structure:
      - Sell 1 ATM call  (at atm_strike)
      - Sell 1 ATM put   (at atm_strike)
      - Buy  1 OTM call  (at atm_strike + wing_width)
      - Buy  1 OTM put   (at atm_strike - wing_width)

    Requires Level 3 options approval + ENABLE_OPTIONS=true in env.
    """
    from config import ENABLE_OPTIONS
    if not ENABLE_OPTIONS:
        return {"status": "skipped",
                "reason": "Options trading disabled — set ENABLE_OPTIONS=true after Level 3 approval"}

    if not is_configured():
        return {"status": "skipped", "reason": "Alpaca not configured"}

    # CRITICAL audit C-10: options also gated by daily loss limit.
    if not _check_daily_loss_limit():
        return {"status": "rejected_loss_limit",
                "reason": "Daily loss limit hit — options path also halted"}

    mode = "LIVE" if is_live_mode() else "PAPER"

    from execution.options_utils import build_option_symbol
    sell_call = build_option_symbol(ticker, expiry_yymmdd, "C", atm_strike)
    sell_put  = build_option_symbol(ticker, expiry_yymmdd, "P", atm_strike)
    buy_call  = build_option_symbol(ticker, expiry_yymmdd, "C", atm_strike + wing_width)
    buy_put   = build_option_symbol(ticker, expiry_yymmdd, "P", atm_strike - wing_width)

    print(f"[APEX] [{mode}] IRON BUTTERFLY {ticker} exp={expiry_yymmdd} "
          f"ATM={atm_strike} wings=±{wing_width}")
    print(f"         Sell {sell_call} · Sell {sell_put}")
    print(f"         Buy  {buy_call} · Buy  {buy_put}")

    try:
        from alpaca.trading.requests import OptionLegRequest, MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

        legs = [
            OptionLegRequest(symbol=sell_call, side=OrderSide.SELL, ratio_qty=1),
            OptionLegRequest(symbol=sell_put,  side=OrderSide.SELL, ratio_qty=1),
            OptionLegRequest(symbol=buy_call,  side=OrderSide.BUY,  ratio_qty=1),
            OptionLegRequest(symbol=buy_put,   side=OrderSide.BUY,  ratio_qty=1),
        ]
        order_req = MarketOrderRequest(
            qty           = contracts,
            time_in_force = TimeInForce.DAY,
            order_class   = OrderClass.MLEG,
            legs          = legs,
        )
        client = _get_client()
        order  = client.submit_order(order_req)

        result = {
            "status":      "submitted",
            "order_id":    str(order.id),
            "ticker":      ticker,
            "side":        "iron_butterfly",
            "asset_class": "options",
            "legs":        [sell_call, sell_put, buy_call, buy_put],
            "atm_strike":  atm_strike,
            "wing_width":  wing_width,
            "expiry":      expiry_yymmdd,
            "contracts":   contracts,
            "mode":        mode,
            "timestamp":   datetime.now().isoformat(),
            "reason":      reason,
        }
        try:
            import db
            if db.db_available():
                db.save_trade(result)
        except Exception:
            pass
        return result

    except Exception as e:
        print(f"[APEX] Iron butterfly failed for {ticker}: {e}")
        return {"status": "error", "reason": str(e), "ticker": ticker}
