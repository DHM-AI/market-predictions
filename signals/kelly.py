"""
Kelly Criterion risk agent.

Given the model's edge (win probability) and a bankroll,
calculates the optimal fraction to risk per trade and the dollar amount.

Formula: f* = (p * b - q) / b
  p = probability of winning (our XGB/blended score normalized to 0-1)
  q = 1 - p (probability of losing)
  b = win/loss ratio (expected gain / expected loss)

For stock moves we assume:
  - Win: stock moves +5% (our target)
  - Loss: stock moves -3% (typical stop loss)
  So b = 5/3 ≈ 1.67

We apply a half-Kelly for safety (standard professional practice).
"""
from config import BANKROLL, KELLY_WIN_PCT, KELLY_LOSS_PCT, KELLY_FRACTION, MAX_POSITION_PCT


def kelly_fraction(win_prob: float,
                   win_pct: float = None,
                   loss_pct: float = None) -> float:
    """
    Calculate the full Kelly fraction.
    win_prob: probability of a winning trade (0-1)
    win_pct:  expected gain if win (e.g. 0.05 for 5%)
    loss_pct: expected loss if wrong (e.g. 0.03 for 3%)
    """
    win_pct  = win_pct  if win_pct  is not None else KELLY_WIN_PCT
    loss_pct = loss_pct if loss_pct is not None else KELLY_LOSS_PCT
    if win_prob <= 0 or win_prob >= 1 or loss_pct == 0:
        return 0.0
    b = win_pct / loss_pct   # win/loss ratio
    q = 1 - win_prob
    f = (win_prob * b - q) / b
    return max(0.0, f)


def position_size(win_prob: float,
                  bankroll: float = None,
                  half_kelly: bool = True) -> dict:
    """
    Returns full position sizing recommendation.

    Args:
        win_prob:   model probability (0-1) of a 5%+ move
        bankroll:   total capital available (defaults to config BANKROLL)
        half_kelly: use half-Kelly for safety (recommended)

    Returns dict with:
        fraction:       optimal fraction of bankroll to risk
        dollar_amount:  dollar value to put in
        shares_at_price: placeholder (filled by agent with current price)
        risk_level:     "aggressive" / "moderate" / "conservative" / "skip"
    """
    bankroll = bankroll or BANKROLL
    f = kelly_fraction(win_prob)

    if half_kelly:
        f = f / 2.0

    # Hard cap at MAX_POSITION_PCT
    f = min(f, MAX_POSITION_PCT)

    dollar = round(bankroll * f, 2)

    if f >= 0.06:
        risk_level = "aggressive"
    elif f >= 0.03:
        risk_level = "moderate"
    elif f > 0:
        risk_level = "conservative"
    else:
        risk_level = "skip"

    return {
        "kelly_fraction": round(f, 4),
        "dollar_amount": dollar,
        "pct_of_bankroll": round(f * 100, 2),
        "risk_level": risk_level,
        "bankroll": bankroll,
    }


def annotate_picks(picks_df, bankroll: float = None):
    """Add Kelly position sizing columns to a scored picks DataFrame."""
    import pandas as pd
    if picks_df is None or picks_df.empty:
        return picks_df

    bankroll = bankroll or BANKROLL

    # Drop any pre-existing sizing columns to prevent duplicate columns on re-runs
    sizing_cols = ["kelly_fraction", "dollar_amount", "pct_of_bankroll", "risk_level", "bankroll"]
    picks_df = picks_df.drop(columns=[c for c in sizing_cols if c in picks_df.columns], errors="ignore")

    sizing = picks_df.apply(
        lambda row: position_size(
            win_prob=min(row.get("xgb_prob", row.get("score", 50) / 100), 0.99),
            bankroll=bankroll,
        ),
        axis=1,
        result_type="expand",
    )
    return pd.concat([picks_df, sizing], axis=1)
