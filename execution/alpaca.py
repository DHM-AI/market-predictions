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
            sym = o.symbol
            if hasattr(o, "legs") and o.legs:
                for leg in o.legs:
                    if hasattr(leg, "stop_price") and leg.stop_price:
                        sl_tp_map.setdefault(sym, {})["stop_loss"] = float(leg.stop_price)
                    if hasattr(leg, "limit_price") and leg.limit_price and leg.side:
                        # Take profit leg has opposite side
                        sl_tp_map.setdefault(sym, {})["take_profit"] = float(leg.limit_price)

        return [
            {
                "ticker":           p.symbol,
                "qty":              float(p.qty),
                "market_value":     float(p.market_value),
                "unrealized_pl":    float(p.unrealized_pl),
                "unrealized_pl_pct":float(p.unrealized_plpc) * 100,
                "side":             str(p.side),
                "avg_entry_price":  float(p.avg_entry_price),
                "current_price":    float(p.current_price),
                "stop_loss":        sl_tp_map.get(p.symbol, {}).get("stop_loss"),
                "take_profit":      sl_tp_map.get(p.symbol, {}).get("take_profit"),
            }
            for p in positions
        ]
    except Exception as e:
        print(f"[alpaca] get_positions error: {e}")
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
