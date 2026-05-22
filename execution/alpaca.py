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
    return {
        "buying_power":    float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
        "cash":            float(acct.cash),
        "equity":          float(acct.equity),
        "last_equity":     float(acct.last_equity) if acct.last_equity else float(acct.equity),
        "paper":           not ALPACA_LIVE_MODE,
    }


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
                reason: str = "") -> dict:
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

    # Fallback: try yfinance if Alpaca data feed fails
    if price is None or price <= 0:
        try:
            import yfinance as yf
            hist = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                print(f"[APEX] Used yfinance price for {ticker}: ${price:.2f}")
        except Exception:
            pass

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
        }

        try:
            import db
            if db.db_available():
                db.save_trade(result)
        except Exception:
            pass

        return result

    except Exception as e:
        print(f"[APEX] Bracket order failed: {e}. Falling back to simple order.")
        return _place_simple_order(ticker, dollar_amount, side, mode, reason)


def _place_simple_order(ticker: str, dollar_amount: float, side: str,
                         mode: str, reason: str) -> dict:
    """Fallback: plain market order without bracket (futures, etc.)

    For SELL (short) orders we always use qty — Alpaca rejects notional shorts.
    For BUY orders we prefer notional, fall back to qty if needed.
    """
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
    """Return open positions with SL/TP info from open orders."""
    if not is_configured():
        return []
    try:
        client    = _get_client()
        positions = client.get_all_positions()
        # Get open bracket orders to find SL/TP levels
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        orders    = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
        sl_tp_map = {}  # ticker → {stop_loss, take_profit}
        for o in orders:
            sym   = o.symbol
            otype = str(getattr(o, "type", "")).lower()
            # After bracket fills, child orders appear as standalone open orders:
            # TP leg → OrderType.LIMIT  (limit_price set)
            # SL leg → OrderType.STOP   (stop_price set)
            if "limit" in otype and not "stop" in otype:
                lp = getattr(o, "limit_price", None)
                if lp:
                    sl_tp_map.setdefault(sym, {})["take_profit"] = float(lp)
            if "stop" in otype and "trailing" not in otype:  # exclude trailing stops — no static price
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
            # Fall back to computing from config constants when Alpaca doesn't expose the leg
            is_short = "short" in str(getattr(p, "side", "")).lower()
            if is_short:
                # For short positions: SL is above entry (buy-to-cover), TP is below entry
                sl = known.get("stop_loss")  or round(entry * (1 + KELLY_LOSS_PCT), 2)
                tp = known.get("take_profit") or round(entry * (1 - MOVE_TARGET_PCT), 2)
            else:
                # For long positions: SL is below entry, TP is above entry
                sl = known.get("stop_loss")  or round(entry * (1 - KELLY_LOSS_PCT), 2)
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

        results = []
        for ticker, orders in by_ticker.items():
            buys  = sorted([o for o in orders if "buy"  in str(o.side).lower()],
                           key=lambda o: o.filled_at)
            sells = sorted([o for o in orders if "sell" in str(o.side).lower()],
                           key=lambda o: o.filled_at)

            # ── LONG exits: sell closes a prior buy ─────────────────────────
            for sell in sells:
                prior_buys = [b for b in buys if b.filled_at < sell.filled_at]
                if not prior_buys:
                    continue
                buy = prior_buys[-1]

                entry_price = float(buy.filled_avg_price)
                exit_price  = float(sell.filled_avg_price)
                qty         = float(sell.filled_qty)

                realized_pnl     = round((exit_price - entry_price) * qty, 2)
                realized_pnl_pct = round((exit_price / entry_price - 1) * 100, 2) if entry_price else 0

                sell_type = str(getattr(sell, "type", "")).lower()
                if "limit" in sell_type and realized_pnl > 0:
                    outcome = "tp_hit"
                elif "stop" in sell_type and realized_pnl < 0:
                    outcome = "sl_hit"
                else:
                    outcome = "manual"

                results.append({
                    "ticker":           ticker,
                    "qty":              qty,
                    "entry_price":      round(entry_price, 2),
                    "exit_price":       round(exit_price, 2),
                    "realized_pnl":     realized_pnl,
                    "realized_pnl_pct": realized_pnl_pct,
                    "outcome":          outcome,
                    "closed_at":        str(sell.filled_at)[:16].replace("T", " "),
                })

            # ── SHORT exits: buy-to-cover closes a prior sell ────────────────
            for buy in buys:
                prior_sells = [s for s in sells if s.filled_at < buy.filled_at]
                if not prior_sells:
                    continue
                # Check this buy isn't already used as a long entry
                # (if there's a prior buy before this sell, it's a long entry not a short)
                entry_sell = prior_sells[-1]
                # Only treat as short exit if the sell came before this buy
                # AND there's no prior buy (i.e., the position was opened by a sell)
                prior_buys_before_sell = [b2 for b2 in buys if b2.filled_at < entry_sell.filled_at]
                if prior_buys_before_sell:
                    continue  # there was a buy before the sell → long trade, already handled

                entry_price = float(entry_sell.filled_avg_price)
                exit_price  = float(buy.filled_avg_price)
                qty         = float(buy.filled_qty)

                # Short P&L: profit when exit (cover) is below entry (short)
                realized_pnl     = round((entry_price - exit_price) * qty, 2)
                realized_pnl_pct = round((entry_price / exit_price - 1) * 100, 2) if exit_price else 0

                buy_type = str(getattr(buy, "type", "")).lower()
                if "limit" in buy_type and realized_pnl > 0:
                    outcome = "tp_hit"
                elif "stop" in buy_type and realized_pnl < 0:
                    outcome = "sl_hit"
                else:
                    outcome = "manual"

                results.append({
                    "ticker":           ticker,
                    "qty":              qty,
                    "entry_price":      round(entry_price, 2),
                    "exit_price":       round(exit_price, 2),
                    "realized_pnl":     realized_pnl,
                    "realized_pnl_pct": realized_pnl_pct,
                    "outcome":          outcome,
                    "closed_at":        str(buy.filled_at)[:16].replace("T", " "),
                })

        # Deduplicate (same ticker+closed_at can appear from both loops on mixed books)
        seen = set()
        deduped = []
        for r in results:
            key = (r["ticker"], r["closed_at"], r["realized_pnl"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        return sorted(deduped, key=lambda x: x["closed_at"], reverse=True)

    except Exception as e:
        print(f"[APEX] get_closed_trade_pnl error: {e}")
        return []


def close_position(ticker: str) -> dict:
    """Close an open position immediately at market price."""
    if not is_configured():
        return {"status": "skipped"}
    try:
        client = _get_client()
        # Cancel any open bracket orders first
        try:
            orders = client.get_orders()
            for o in orders:
                if o.symbol == ticker:
                    client.cancel_order_by_id(str(o.id))
        except Exception:
            pass
        # Close the position
        client.close_position(ticker)
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

        # Cancel existing stop orders for this ticker
        open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
        cancelled = 0
        qty = 0
        for o in open_orders:
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

    Already-trailing positions are detected by order type and skipped,
    so this is safe to call repeatedly.

    Returns a list of dicts for positions that were upgraded to trailing.
    """
    from config import TRAIL_TRIGGER_PCT, TRAIL_PCT

    trigger = trigger_pct if trigger_pct is not None else TRAIL_TRIGGER_PCT
    trail   = trail_pct   if trail_pct   is not None else TRAIL_PCT

    if not is_configured():
        return []

    results = []
    try:
        from alpaca.trading.requests import (GetOrdersRequest,
                                              TrailingStopOrderRequest)
        from alpaca.trading.enums import (QueryOrderStatus, OrderSide,
                                          TimeInForce)

        client    = _get_client()
        positions = get_positions()
        if not positions:
            return []

        # Build map: ticker → open order list
        open_orders = client.get_orders(
            GetOrdersRequest(status=QueryOrderStatus.OPEN))
        orders_by_ticker: dict = {}
        for o in open_orders:
            orders_by_ticker.setdefault(o.symbol, []).append(o)

        for p in positions:
            ticker   = p["ticker"]
            pct_gain = p.get("unrealized_pl_pct", 0)  # already in %
            qty      = p["qty"]
            raw_side = str(p.get("side", "")).lower()
            is_long  = "long" in raw_side or "buy" in raw_side

            # Only handle longs for now; shorts need inverted logic
            if not is_long:
                continue

            # Not profitable enough yet
            if pct_gain < trigger * 100:
                continue

            ticker_orders = orders_by_ticker.get(ticker, [])

            # Skip if a trailing stop already exists for this ticker
            already_trailing = any(
                "trailing" in str(getattr(o, "type", "")).lower()
                for o in ticker_orders
            )
            if already_trailing:
                print(f"[AEGIS] {ticker} already has a trailing stop — skipping")
                continue

            # Process each position in its own try/except so one failure
            # (e.g. fractional share DAY-only restriction) doesn't kill the loop
            try:
                # Cancel existing fixed stop-loss order(s)
                cancelled = 0
                for o in ticker_orders:
                    otype = str(getattr(o, "type", "")).lower()
                    if "stop" in otype and "limit" not in otype:
                        try:
                            client.cancel_order_by_id(str(o.id))
                            cancelled += 1
                        except Exception as ce:
                            print(f"[AEGIS] Could not cancel SL for {ticker}: {ce}")

                # Place native Alpaca trailing stop — try GTC first, DAY fallback for fractionals
                trail_pct_val = trail * 100   # Alpaca wants e.g. 3.0 for 3%
                assert 0.5 <= trail_pct_val <= 20, f"trail_percent {trail_pct_val} out of sane range"
                order = None
                for tif in [TimeInForce.GTC, TimeInForce.DAY]:
                    try:
                        trail_req = TrailingStopOrderRequest(
                            symbol        = ticker,
                            qty           = qty,
                            side          = OrderSide.SELL,
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
                print(f"[AEGIS] {ticker} error: {e} — skipping")

    except Exception as e:
        print(f"[AEGIS] trail_positions error: {e}")

    return results


def cancel_all_orders() -> int:
    """Cancel all open orders. Returns count cancelled."""
    if not is_configured():
        return 0
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        client = _get_client()
        orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
        for o in orders:
            try:
                client.cancel_order_by_id(str(o.id))
            except Exception:
                pass
        return len(orders)
    except Exception:
        return 0
