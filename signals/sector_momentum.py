from __future__ import annotations
"""
Sector momentum signal — boost picks whose sector ETF is above its 50MA.

No extra API call required — reads the per-sector status that
`market_regime.get_market_regime()` already computes.

Public API:
    get_sector_momentum(ticker, regime=None) -> dict
        Returns:
          {
            "triggered": bool,    # ticker's sector ETF is above 50MA
            "sector_etf":  str,   # "XLK", "XLF", etc., or None
            "above_50ma":  bool,
            "strength":    float, # 0..1
            "summary":     str,
          }
"""
from signals.market_regime import get_market_regime


# Ticker → sector ETF map. Covers full S&P 500 + popular non-S&P + crypto/futures.
# Sectors flow through to the 11 SPDR ETFs (XLK/XLF/XLV/etc.) which we already
# track in market_regime.
_TICKER_TO_ETF = {
    # Tech → XLK
    "AAPL":"XLK","MSFT":"XLK","NVDA":"XLK","AVGO":"XLK","ORCL":"XLK","CRM":"XLK",
    "ADBE":"XLK","CSCO":"XLK","AMD":"XLK","INTC":"XLK","IBM":"XLK","QCOM":"XLK",
    "TXN":"XLK","AMAT":"XLK","MU":"XLK","LRCX":"XLK","KLAC":"XLK","ADI":"XLK",
    "PANW":"XLK","SNPS":"XLK","CDNS":"XLK","ANET":"XLK","FTNT":"XLK","NOW":"XLK",
    "INTU":"XLK","WDAY":"XLK","TEAM":"XLK","DDOG":"XLK","ZS":"XLK","CRWD":"XLK",
    "SNOW":"XLK","NET":"XLK","MDB":"XLK","SHOP":"XLK","SMCI":"XLK","PLTR":"XLK",
    "ARM":"XLK","ACN":"XLK","ROP":"XLK","NXPI":"XLK","MRVL":"XLK","MCHP":"XLK",
    "FSLR":"XLK","ENPH":"XLK","DELL":"XLK","HPQ":"XLK","ON":"XLK",

    # Communication → XLC
    "GOOGL":"XLC","GOOG":"XLC","META":"XLC","NFLX":"XLC","DIS":"XLC","CMCSA":"XLC",
    "VZ":"XLC","T":"XLC","TMUS":"XLC","CHTR":"XLC","EA":"XLC","TTWO":"XLC",
    "RBLX":"XLC","SPOT":"XLC","SNAP":"XLC","MTCH":"XLC","WBD":"XLC","PARA":"XLC",
    "PINS":"XLC","ROKU":"XLC","TTD":"XLC","DASH":"XLC",

    # Consumer Disc → XLY
    "AMZN":"XLY","TSLA":"XLY","HD":"XLY","MCD":"XLY","NKE":"XLY","LOW":"XLY",
    "SBUX":"XLY","BKNG":"XLY","TJX":"XLY","CMG":"XLY","ORLY":"XLY","MAR":"XLY",
    "ABNB":"XLY","HLT":"XLY","F":"XLY","GM":"XLY","LULU":"XLY","ROST":"XLY",
    "AZO":"XLY","YUM":"XLY","CCL":"XLY","RCL":"XLY","NCLH":"XLY","DRI":"XLY",
    "EBAY":"XLY","DPZ":"XLY","CHWY":"XLY","RIVN":"XLY","LCID":"XLY","ULTA":"XLY",
    "DKNG":"XLY","DG":"XLY","DLTR":"XLY",

    # Consumer Staples → XLP
    "WMT":"XLP","PG":"XLP","KO":"XLP","PEP":"XLP","COST":"XLP","PM":"XLP",
    "MO":"XLP","MDLZ":"XLP","CL":"XLP","TGT":"XLP","KMB":"XLP","GIS":"XLP",
    "KR":"XLP","SYY":"XLP","STZ":"XLP","HSY":"XLP","KHC":"XLP","CHD":"XLP",
    "CLX":"XLP","MNST":"XLP","KDP":"XLP","EL":"XLP","MKC":"XLP",

    # Healthcare → XLV
    "LLY":"XLV","UNH":"XLV","JNJ":"XLV","MRK":"XLV","ABBV":"XLV","TMO":"XLV",
    "ABT":"XLV","PFE":"XLV","DHR":"XLV","AMGN":"XLV","ISRG":"XLV","BMY":"XLV",
    "SYK":"XLV","ELV":"XLV","GILD":"XLV","VRTX":"XLV","CVS":"XLV","REGN":"XLV",
    "MDT":"XLV","ZTS":"XLV","CI":"XLV","HUM":"XLV","BSX":"XLV","BDX":"XLV",
    "EW":"XLV","HCA":"XLV","BIIB":"XLV","IDXX":"XLV","DXCM":"XLV","MRNA":"XLV",

    # Financials → XLF
    "BRK.B":"XLF","BRK_B":"XLF","JPM":"XLF","V":"XLF","MA":"XLF","BAC":"XLF",
    "WFC":"XLF","GS":"XLF","MS":"XLF","AXP":"XLF","SCHW":"XLF","BLK":"XLF",
    "C":"XLF","SPGI":"XLF","PGR":"XLF","CB":"XLF","MMC":"XLF","ICE":"XLF",
    "CME":"XLF","USB":"XLF","PNC":"XLF","TFC":"XLF","AON":"XLF","AIG":"XLF",
    "MET":"XLF","PRU":"XLF","AFL":"XLF","TRV":"XLF","BX":"XLF","KKR":"XLF",
    "COF":"XLF","DFS":"XLF","COIN":"XLF","HOOD":"XLF","SOFI":"XLF","PYPL":"XLF",
    "SQ":"XLF","FIS":"XLF",

    # Industrials → XLI
    "CAT":"XLI","BA":"XLI","HON":"XLI","UPS":"XLI","RTX":"XLI","GE":"XLI",
    "LMT":"XLI","UNP":"XLI","DE":"XLI","ETN":"XLI","MMM":"XLI","FDX":"XLI",
    "CSX":"XLI","NSC":"XLI","WM":"XLI","GD":"XLI","NOC":"XLI","EMR":"XLI",
    "ITW":"XLI","JCI":"XLI","PCAR":"XLI","PH":"XLI","CMI":"XLI","CARR":"XLI",
    "OTIS":"XLI","LUV":"XLI","DAL":"XLI","UAL":"XLI","AAL":"XLI","URI":"XLI",
    "PWR":"XLI","FAST":"XLI","ROK":"XLI","TT":"XLI",

    # Energy → XLE
    "XOM":"XLE","CVX":"XLE","COP":"XLE","EOG":"XLE","SLB":"XLE","MPC":"XLE",
    "PSX":"XLE","OXY":"XLE","PXD":"XLE","VLO":"XLE","HES":"XLE","FANG":"XLE",
    "DVN":"XLE","BKR":"XLE","HAL":"XLE","WMB":"XLE","KMI":"XLE","OKE":"XLE",
    "TRGP":"XLE","LNG":"XLE","APA":"XLE","MRO":"XLE","EQT":"XLE",

    # Materials → XLB
    "LIN":"XLB","APD":"XLB","SHW":"XLB","ECL":"XLB","FCX":"XLB","NEM":"XLB",
    "DOW":"XLB","DD":"XLB","NUE":"XLB","PPG":"XLB","CTVA":"XLB","VMC":"XLB",
    "MLM":"XLB","IFF":"XLB","ALB":"XLB","STLD":"XLB","CF":"XLB","LYB":"XLB",
    "EMN":"XLB","FMC":"XLB","MOS":"XLB","GOLD":"XLB",

    # Utilities → XLU
    "NEE":"XLU","SO":"XLU","DUK":"XLU","SRE":"XLU","AEP":"XLU","D":"XLU",
    "PCG":"XLU","EXC":"XLU","XEL":"XLU","ED":"XLU","PEG":"XLU","WEC":"XLU",
    "ES":"XLU","AWK":"XLU","DTE":"XLU","ETR":"XLU","FE":"XLU","AEE":"XLU",
    "PPL":"XLU","CMS":"XLU","EIX":"XLU","NRG":"XLU","VST":"XLU","CEG":"XLU",

    # Real Estate → XLRE
    "PLD":"XLRE","AMT":"XLRE","EQIX":"XLRE","CCI":"XLRE","PSA":"XLRE","O":"XLRE",
    "WELL":"XLRE","SPG":"XLRE","DLR":"XLRE","VICI":"XLRE","AVB":"XLRE","EQR":"XLRE",
    "EXR":"XLRE","IRM":"XLRE","MAA":"XLRE","ESS":"XLRE","ARE":"XLRE","BXP":"XLRE",
}


def _empty(reason: str = "") -> dict:
    return {
        "triggered":   False,
        "sector_etf":  None,
        "above_50ma":  False,
        "strength":    0.0,
        "summary":     reason,
    }


def get_sector_momentum(ticker: str, regime: dict | None = None) -> dict:
    """
    Return sector momentum signal for a ticker.
    Pulls regime status from the (cached) market_regime module.
    """
    if not ticker:
        return _empty()
    etf = _TICKER_TO_ETF.get(ticker.upper().strip())
    if etf is None:
        return _empty("no sector mapping")

    if regime is None:
        try:
            regime = get_market_regime()
        except Exception as e:
            return _empty(f"regime fetch failed: {e}")

    status = (regime or {}).get("sector_status") or {}
    if etf not in status:
        return _empty(f"no status for {etf}")

    above = bool(status[etf])
    if above:
        return {
            "triggered":   True,
            "sector_etf":  etf,
            "above_50ma":  True,
            "strength":    1.0,
            "summary":     f"Sector {etf} above 50MA (wind at back)",
        }
    return {
        "triggered":   False,
        "sector_etf":  etf,
        "above_50ma":  False,
        "strength":    0.0,
        "summary":     "",
    }
