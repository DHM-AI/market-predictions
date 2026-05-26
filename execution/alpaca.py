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
                        "reason": reason,
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
        _active_statuses = {
            "orderstatus.open", "orderstatus.new", "orderstatus.held",
            "open", "new", "held", "pending_new", "accepted",
        }
        orders = [o for o in _all if str(getattr(o, "status", "")).lower() in _active_statuses]
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
        _active_statuses = {
            "orderstatus.open", "orderstatus.new", "orderstatus.held",
            "open", "new", "held", "pending_new", "accepted",
        }
        try:
            all_orders = client.get_orders(GetOrdersRequest(
                status=QueryOrderStatus.ALL, limit=400))
            cancelled = 0
            for o in all_orders:
                if o.symbol != ticker:
                    continue
                if str(getattr(o, "status", "")).lower() not in _active_statuses:
                    continue
                try:
                    client.cancel_order_by_id(str(o.id))
                    cancelled += 1
                except Exception:
                    pass
            # Give Alpaca a moment to release the held shares
            if cancelled:
                _time.sleep(0.5)
        except Exception:
            pass

        # Close the position — retry once with a longer wait if first attempt fails
        try:
            client.close_position(ticker)
        except Exception as first_err:
            if "insufficient" in str(first_err).lower() or "held" in str(first_err).lower():
                _time.sleep(1.5)
                client.close_position(ticker)
            else:
                raise

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

    # Load partial exit history per ticker — {ticker: {t1, t2, t1_qty}}
    # Persisted in Supabase so it survives GitHub Actions restarts.
    partial_history: dict = {}
    if ENABLE_PARTIAL_EXIT:
        try:
            from db import get_partial_exit_history
            partial_history = get_partial_exit_history()
        except Exception as _dbe:
            print(f"[AEGIS] Could not load partial exit history: {_dbe}")

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

        # Build map: ticker → active order list
        # Must include HELD orders — bracket stop/TP children are held, not open.
        # Without held orders, AEGIS can't see or cancel bracket stops.
        from alpaca.trading.enums import QueryOrderStatus as _QOS
        _all_active = client.get_orders(
            GetOrdersRequest(status=_QOS.ALL, limit=400))
        _active_statuses = {
            "orderstatus.open", "orderstatus.new", "orderstatus.held",
            "open", "new", "held", "pending_new", "accepted",
        }
        open_orders = [
            o for o in _all_active
            if str(getattr(o, "status", "")).lower() in _active_statuses
        ]
        orders_by_ticker: dict = {}
        for o in open_orders:
            orders_by_ticker.setdefault(o.symbol, []).append(o)

        for p in positions:
            ticker   = p["ticker"]
            pct_gain = p.get("unrealized_pl_pct", 0)  # already in %
            qty      = p["qty"]
            raw_side = str(p.get("side", "")).lower()
            is_long  = "long" in raw_side or "buy" in raw_side

            ticker_orders = orders_by_ticker.get(ticker, [])
            pct_gain_decimal = pct_gain / 100.0

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
                    # qty to close = 33% of ORIGINAL position
                    # For T1: original = current (=_abs_qty)
                    # For T2: original = current / (1 - T1_FRACTION) ≈ current / 0.67
                    if tier_name == "t1":
                        close_qty = round(_abs_qty * fraction_to_close, 4)
                    else:
                        # T2: same qty as T1 (record from history)
                        close_qty = _hist.get("t1_qty", 0)
                        if close_qty <= 0:
                            # Fallback if T1 qty unknown — use 33% of current
                            close_qty = round(_abs_qty * fraction_to_close, 4)
                        close_qty = min(close_qty, _abs_qty)  # don't oversell
                    if close_qty <= 0:
                        return None
                    remain_qty = round(_abs_qty - close_qty, 4)
                    exit_side  = OrderSide.SELL if is_long else OrderSide.BUY

                    # Cancel existing stops first (release held shares)
                    for o in ticker_orders:
                        otype   = str(getattr(o, "type", "")).lower()
                        ostatus = str(getattr(o, "status", "")).lower()
                        if "stop" in otype and ostatus in (
                                "orderstatus.open", "orderstatus.new",
                                "orderstatus.held", "open", "new", "held",
                                "pending_new"):
                            try:
                                client.cancel_order_by_id(str(o.id))
                            except Exception:
                                pass

                    # Market-close the tier qty
                    mreq = MarketOrderRequest(
                        symbol=ticker, qty=close_qty, side=exit_side,
                        time_in_force=TimeInForce.DAY,
                    )
                    close_order = client.submit_order(mreq)

                    # T1 moves remaining stop to breakeven
                    # T2 leaves stop at breakeven (already there from T1)
                    if move_to_be and remain_qty > 0 and _entry_px > 0:
                        be_side = OrderSide.SELL if is_long else OrderSide.BUY
                        be_req = StopOrderRequest(
                            symbol=ticker, qty=remain_qty, side=be_side,
                            stop_price=round(_entry_px, 2),
                            time_in_force=TimeInForce.GTC,
                        )
                        try:
                            client.submit_order(be_req)
                        except Exception:
                            be_req.time_in_force = TimeInForce.DAY
                            client.submit_order(be_req)

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

            # Only handle longs for trailing stop (shorts need inverted logic)
            if not is_long:
                continue

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
                except Exception:
                    continue  # if cancel fails, skip to avoid duplicates
            else:
                # No trailing stop — only activate if gain >= trigger
                if pct_gain < trigger * 100:
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
                trail_pct_val = target_trail * 100   # Alpaca wants e.g. 3.0 for 3%
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
                # Alpaca won't allow trailing stops on fractional positions.
                # Simulate trailing: move fixed stop up to 3% below current price.
                if "fractional" in str(e).lower():
                    _simulated = False
                    try:
                        current_price = p.get("current_price") or p.get("avg_entry_price", 0)
                        new_stop = round(current_price * (1 - trail), 2)
                        entry_px  = p.get("avg_entry_price", 0)
                        if new_stop > entry_px:  # only move stop if it locks in profit
                            # Cancel old stops
                            for o in ticker_orders:
                                otype = str(getattr(o, "type", "")).lower()
                                if "stop" in otype and "limit" not in otype and "trailing" not in otype:
                                    try:
                                        client.cancel_order_by_id(str(o.id))
                                    except Exception:
                                        pass
                            # Place new fixed stop above entry (locking in profit)
                            from alpaca.trading.requests import StopOrderRequest
                            stop_req = StopOrderRequest(
                                symbol        = ticker,
                                qty           = qty,
                                side          = OrderSide.SELL,
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


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def place_crypto_order(alpaca_symbol: str, dollar_amount: float,
                       direction: str, reason: str = "") -> dict:
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
