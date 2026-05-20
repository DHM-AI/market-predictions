import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time


def get_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"[fetcher] {ticker}: {e}")
        return pd.DataFrame()


def get_ohlcv_batch(tickers: list[str], period: str = "1y",
                    chunk_size: int = 50, delay: float = 1.0) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        try:
            raw = yf.download(chunk, period=period, interval="1d",
                              progress=False, auto_adjust=True, group_by="ticker")
            for ticker in chunk:
                try:
                    if len(chunk) == 1:
                        df = raw.copy()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                    else:
                        df = raw[ticker].copy()
                        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                    df = df.dropna(how="all")
                    if not df.empty:
                        results[ticker] = df
                except Exception:
                    results[ticker] = get_ohlcv(ticker, period=period)
        except Exception as e:
            print(f"[fetcher] batch error chunk {i}: {e}")
            for ticker in chunk:
                results[ticker] = get_ohlcv(ticker, period=period)
        if i + chunk_size < len(tickers):
            time.sleep(delay)
    return results


def get_earnings_days(ticker: str) -> Optional[int]:
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is None:
            return None
        # calendar may be a dict or DataFrame depending on yfinance version
        if isinstance(cal, dict):
            date_val = cal.get("Earnings Date")
            if date_val is None:
                return None
            if isinstance(date_val, list):
                date_val = date_val[0]
            earnings_dt = pd.to_datetime(date_val)
        elif isinstance(cal, pd.DataFrame):
            if "Earnings Date" in cal.columns:
                date_val = cal["Earnings Date"].iloc[0]
            elif "Earnings Date" in cal.index:
                date_val = cal.loc["Earnings Date"].iloc[0]
            else:
                return None
            earnings_dt = pd.to_datetime(date_val)
        else:
            return None
        delta = (earnings_dt.date() - datetime.today().date()).days
        return delta
    except Exception:
        return None


def get_recent_news(ticker: str) -> list[dict]:
    try:
        t = yf.Ticker(ticker)
        return t.news or []
    except Exception:
        return []
