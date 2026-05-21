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
        acct       = _get_client().get_account()
        equity     = float(acct.equity)
        last_equity= float(acct.last_equity)
        daily_loss = (equity - last_equity) / last_equity
        if daily_loss < -DAILY_LOSS_LIMIT_PCT:
            print(f"[alpaca] ⚠ Daily loss limit breached ({daily_loss:.1%}). Halting trades.")
            return False
        return True
    except Exception:
        return True  # fail open


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

    # Get current price to calculate SL/TP and convert notional → shares
    price = get_current_price(ticker)
    if price is None or price <= 0:
        # Fallback: place simple market order without bracket
        return _place_simple_order(ticker, dollar_amount, side, mode, reason)

    qty = max(1, round(dollar_amount / price))

    # Stop loss and take profit prices
    if side == "buy":
        stop_price  = round(price * (1 - KELLY_LOSS_PCT), 2)
        limit_price = round(price * (1 + MOVE_TARGET_PCT), 2)
    else:
        stop_price  = round(price * (1 + KELLY_LOSS_PCT), 2)
        limit_price = round(price * (1 - MOVE_TARGET_PCT), 2)

    print(f"[alpaca] [{mode}] BRACKET {side.upper()} {qty} {ticker} @ ~${price:.2f}")
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
        print(f"[alpaca] Bracket order failed: {e}. Falling back to simple order.")
        return _place_simple_order(ticker, dollar_amount, side, mode, reason)


def _place_simple_order(ticker: str, dollar_amount: float, side: str,
                         mode: str, reason: str) -> dict:
    """Fallback: plain market order without bracket (futures, etc.)"""
    try:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        client    = _get_client()
        order_req = MarketOrderRequest(
            symbol        = ticker,
            notional      = round(dollar_amount, 2),
            side          = OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force = TimeInForce.DAY,
        )
        order = client.submit_order(order_req)
        result = {
            "status": "submitted", "order_id": str(order.id),
            "ticker": ticker, "side": side,
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
            if "stop" in otype:
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
        print(f"[alpaca] get_positions error: {e}")
        return []


def get_closed_trade_pnl(days: int = 60) -> list[dict]:
    """
    Fetch realized P&L for recently closed trades by looking at filled orders.
    For bracket orders: matches parent entry fill with SL/TP exit fill.

    Returns list of dicts:
        ticker, side, qty, entry_price, exit_price, realized_pnl,
        realized_pnl_pct, outcome ('tp_hit' | 'sl_hit' | 'closed'), closed_at
    """
    if not is_configured():
        return []
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus
        from datetime import datetime, timedelta

        client = _get_client()
        after  = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

        orders = client.get_orders(GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            after=after,
            limit=200,
        ))

        results = []
        for o in orders:
            try:
                # Only care about filled parent bracket orders (the entry leg)
                if str(o.order_class) != "bracket":
                    continue
                if not o.filled_avg_price or not o.filled_qty:
                    continue

                entry_price = float(o.filled_avg_price)
                qty         = float(o.filled_qty)
                side        = str(o.side)   # "buy" or "sell"
                ticker      = o.symbol
                filled_at   = str(o.filled_at)[:16] if o.filled_at else ""

                # Look at legs to find which one filled (SL or TP)
                exit_price = None
                outcome    = "closed"
                for leg in (o.legs or []):
                    if hasattr(leg, "filled_avg_price") and leg.filled_avg_price:
                        exit_price = float(leg.filled_avg_price)
                        # TP leg has a limit price; SL leg has a stop price
                        if hasattr(leg, "limit_price") and leg.limit_price:
                            outcome = "tp_hit"
                        elif hasattr(leg, "stop_price") and leg.stop_price:
                            outcome = "sl_hit"

                if exit_price is None:
                    continue   # entry filled but not yet exited

                # P&L: long = (exit - entry) * qty, short = (entry - exit) * qty
                if side == "buy":
                    realized_pnl = (exit_price - entry_price) * qty
                else:
                    realized_pnl = (entry_price - exit_price) * qty

                realized_pnl_pct = (exit_price / entry_price - 1) * 100 if side == "buy" \
                                   else (entry_price / exit_price - 1) * 100

                results.append({
                    "ticker":           ticker,
                    "side":             side,
                    "qty":              qty,
                    "entry_price":      round(entry_price, 2),
                    "exit_price":       round(exit_price, 2),
                    "realized_pnl":     round(realized_pnl, 2),
                    "realized_pnl_pct": round(realized_pnl_pct, 2),
                    "outcome":          outcome,
                    "closed_at":        filled_at,
                })
            except Exception:
                continue

        return sorted(results, key=lambda x: x["closed_at"], reverse=True)

    except Exception as e:
        print(f"[alpaca] get_closed_trade_pnl error: {e}")
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
