import pandas as pd
from config import FUTURES

_sp500_cache: list[str] | None = None


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


def get_universe() -> list[str]:
    from config import WATCHLIST
    sp500  = get_sp500_tickers()
    extras = [t for t in WATCHLIST if t not in sp500]  # avoid duplicates
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
