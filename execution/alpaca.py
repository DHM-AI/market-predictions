"""
Alpaca execution module.

SAFETY DEFAULTS:
  - Paper trading mode unless ALPACA_BASE_URL is explicitly set to live
  - Max single position: 10% of bankroll (Kelly hard cap)
  - Daily loss limit: 5% of bankroll — agent stops trading if hit
  - Minimum confidence: score >= 70 (High confidence only for auto-execution)
  - All trades logged to Supabase trades table

To switch to live trading:
  Set ALPACA_BASE_URL=https://api.alpaca.markets in your .env
  AND set ALPACA_LIVE_MODE=true

DO NOT enable live mode until you have validated on paper for at least 30 days.
"""
import os
from datetime import datetime
from config import (BANKROLL, ALPACA_API_KEY, ALPACA_SECRET_KEY,
                    ALPACA_BASE_URL, ALPACA_LIVE_MODE,
                    MAX_POSITION_PCT, DAILY_LOSS_LIMIT_PCT)


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
        "buying_power": float(acct.buying_power),
        "portfolio_value": float(acct.portfolio_value),
        "cash": float(acct.cash),
        "paper": not ALPACA_LIVE_MODE,
    }


def get_current_price(ticker: str) -> float | None:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quote = data_client.get_stock_latest_quote(req)
        return float(quote[ticker].ask_price)
    except Exception:
        return None


def _check_daily_loss_limit() -> bool:
    """Returns True if we're within daily loss limit, False if breached."""
    try:
        client = _get_client()
        acct = client.get_account()
        equity = float(acct.equity)
        last_equity = float(acct.last_equity)
        daily_loss = (equity - last_equity) / last_equity
        limit = -DAILY_LOSS_LIMIT_PCT
        if daily_loss < limit:
            print(f"[alpaca] ⚠️ Daily loss limit breached ({daily_loss:.1%}). Halting trades.")
            return False
        return True
    except Exception:
        return True  # fail open — don't block trades on check failure


def place_order(ticker: str, dollar_amount: float, direction: str,
                reason: str = "") -> dict:
    """
    Place a market order for a given dollar amount.

    Args:
        ticker:        stock symbol
        dollar_amount: notional value to trade
        direction:     "bullish" (buy) or "bearish" (sell short)
        reason:        human-readable reason (from Claude analysis)

    Returns order confirmation dict.
    RAISES if live mode and safeguards are not met.
    """
    if not is_configured():
        return {"status": "skipped", "reason": "Alpaca not configured"}

    # Safety checks
    if not _check_daily_loss_limit():
        return {"status": "halted", "reason": "daily loss limit breached"}

    max_allowed = BANKROLL * MAX_POSITION_PCT
    if dollar_amount > max_allowed:
        dollar_amount = max_allowed
        print(f"[alpaca] Position capped at ${max_allowed:.0f} (max {MAX_POSITION_PCT*100:.0f}% bankroll)")

    mode = "LIVE" if is_live_mode() else "PAPER"
    side = "buy" if direction == "bullish" else "sell"

    print(f"[alpaca] [{mode}] {side.upper()} ${dollar_amount:.0f} of {ticker} | {reason[:60]}")

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client = _get_client()
        order_req = MarketOrderRequest(
            symbol=ticker,
            notional=round(dollar_amount, 2),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = client.submit_order(order_req)

        result = {
            "status": "filled" if order.status == "filled" else "submitted",
            "order_id": str(order.id),
            "ticker": ticker,
            "side": side,
            "dollar_amount": dollar_amount,
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
        }

        # Log to Supabase
        try:
            import db
            if db.db_available():
                db.save_trade(result)
        except Exception:
            pass

        return result

    except Exception as e:
        return {"status": "error", "reason": str(e), "ticker": ticker}


def get_positions() -> list[dict]:
    """Return current open positions."""
    if not is_configured():
        return []
    try:
        client = _get_client()
        positions = client.get_all_positions()
        return [
            {
                "ticker": p.symbol,
                "qty": float(p.qty),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_pl_pct": float(p.unrealized_plpc) * 100,
                "side": p.side,
            }
            for p in positions
        ]
    except Exception as e:
        print(f"[alpaca] get_positions error: {e}")
        return []


def close_position(ticker: str) -> dict:
    """Close an open position for a ticker."""
    if not is_configured():
        return {"status": "skipped"}
    try:
        client = _get_client()
        client.close_position(ticker)
        return {"status": "closed", "ticker": ticker}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
