from __future__ import annotations
import pandas as pd
from config import FUTURES

_sp500_cache: list[str] | None = None
_ipo_cache:   list[str] | None = None


def get_sp500_tickers() -> list[str]:
    global _sp500_cache
    if _sp500_cache is not None:
        return _sp500_cache
    try:
        import requests
        from io import StringIO
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0 (compatible; MarketPredictions/1.0)"},
            timeout=15,
        )
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        tickers = tables[0]["Symbol"].tolist()
        tickers = [t.replace(".", "-") for t in tickers]
        _sp500_cache = tickers
        return tickers
    except Exception as e:
        print(f"[universe] Wikipedia fetch failed: {e}. Using fallback list.")
        return _get_fallback_tickers()


def get_recent_ipos(months: int = 12, min_volume: int = 1_000_000) -> list[str]:
    """
    Return tickers for stocks that IPO'd within the last `months` months
    and have avg daily volume ≥ min_volume.
    Uses Alpha Vantage LISTING_STATUS endpoint (free tier).
    Falls back to empty list on any error.
    """
    global _ipo_cache
    if _ipo_cache is not None:
        return _ipo_cache

    try:
        import requests
        from datetime import datetime, timedelta
        from config import ALPHA_VANTAGE_KEY, IPO_LOOKBACK_MONTHS, IPO_MIN_VOLUME

        lookback_months = months or IPO_LOOKBACK_MONTHS
        min_vol         = min_volume or IPO_MIN_VOLUME
        cutoff          = datetime.today() - timedelta(days=lookback_months * 30)
        cutoff_str      = cutoff.strftime("%Y-%m-%d")

        url  = (f"https://www.alphavantage.co/query"
                f"?function=LISTING_STATUS&state=active&apikey={ALPHA_VANTAGE_KEY}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()

        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))

        # Filter to recent IPOs on major US exchanges
        df = df[df["ipoDate"] >= cutoff_str]
        df = df[df["exchange"].isin(["NYSE", "NASDAQ", "NYSE ARCA", "NASDAQ NMS"])]
        df = df[df["assetType"] == "Stock"]

        candidates = df["symbol"].tolist()

        # Filter by volume using yfinance (batch check)
        import yfinance as yf
        valid = []
        if candidates:
            data = yf.download(candidates, period="30d", interval="1d",
                               progress=False, auto_adjust=True, group_by="ticker")
            for ticker in candidates:
                try:
                    if len(candidates) == 1:
                        vol = data["Volume"].mean()
                    else:
                        vol = data[ticker]["Volume"].mean() if ticker in data.columns.get_level_values(0) else 0
                    if vol >= min_vol:
                        valid.append(ticker)
                except Exception:
                    pass

        print(f"[universe] Found {len(valid)} recent IPOs (last {lookback_months}mo, vol≥{min_vol:,})")
        _ipo_cache = valid
        return valid

    except Exception as e:
        print(f"[universe] IPO fetch failed: {e}")
        _ipo_cache = []
        return []


def get_universe() -> list[str]:
    from config import WATCHLIST
    sp500    = get_sp500_tickers()
    ipos     = get_recent_ipos()
    seen     = set(sp500)
    extras   = []
    for t in WATCHLIST + ipos:
        if t not in seen:
            extras.append(t)
            seen.add(t)
    return sp500 + extras + FUTURES


def _get_fallback_tickers() -> list[str]:
    return [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY",
        "AVGO", "TSLA", "JPM", "V", "UNH", "XOM", "MA", "COST", "HD", "PG", "JNJ",
        "ABBV", "WMT", "BAC", "NFLX", "MRK", "CRM", "CVX", "KO", "ORCL", "PEP",
        "ACN", "TMO", "AMD", "MCD", "CSCO", "LIN", "ADBE", "ABT", "DIS", "TXN",
        "WFC", "PM", "INTU", "NOW", "NEE", "CAT", "IBM", "GS", "ISRG", "UBER",
        "AXP", "SPGI", "RTX", "GE", "BKNG", "PFE", "AMGN", "HON", "VRTX", "T",
        "QCOM", "SYK", "LOW", "TJX", "C", "BLK", "UNP", "DHR", "BMY", "SCHW",
        "PLD", "DE", "ANET", "MDT", "BA", "MS", "MU", "GILD", "KKR", "ELV",
        "CI", "SO", "CB", "REGN", "UPS", "MMC", "ADP", "PANW", "BSX", "CME",
        "ETN", "ZTS", "LRCX", "ADI", "MO", "ICE", "MCO", "HCA", "SHW", "APH",
    ]
