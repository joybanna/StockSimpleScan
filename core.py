"""
core.py – Shared analysis logic for Stock Scanner
===================================================
All technical-indicator calculations, constants, and the main
``analyze_ticker`` function live here.  Both app.py (Streamlit)
and desktop_app.py (pywebview) import from this module so the
business logic has a single source of truth.
"""

import pandas as pd
import yfinance as yf

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TICKERS: list[str] = ["AAPL", "NVDA", "MSFT", "PTT.BK", "ADVANC.BK", "AOT.BK"]

PRESETS: dict[str, dict] = {
    "Day":   {"interval": "1d",  "dl_period": "6mo", "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Daily"},
    "Week":  {"interval": "1wk", "dl_period": "2y",  "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Weekly"},
    "Month": {"interval": "1mo", "dl_period": "5y",  "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Monthly"},
}

MARKET_MAP: dict[str, tuple[str, str]] = {
    "BK": ("🇹🇭", "Thailand (SET)"),    "HK": ("🇭🇰", "Hong Kong (HKEX)"),
    "L":  ("🇬🇧", "London (LSE)"),      "T":  ("🇯🇵", "Japan (TSE)"),
    "SI": ("🇸🇬", "Singapore (SGX)"),   "AX": ("🇦🇺", "Australia (ASX)"),
    "KS": ("🇰🇷", "South Korea (KRX)"), "SS": ("🇨🇳", "China (Shanghai)"),
    "SZ": ("🇨🇳", "China (Shenzhen)"),  "NS": ("🇮🇳", "India (NSE)"),
    "BO": ("🇮🇳", "India (BSE)"),       "PA": ("🇫🇷", "France (Euronext)"),
    "DE": ("🇩🇪", "Germany (XETRA)"),   "TW": ("🇹🇼", "Taiwan (TWSE)"),
}

FIB_LEVELS: list[float] = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]


# ─────────────────────────────────────────────────────────────────────────────
# Technical Indicator Calculations
# ─────────────────────────────────────────────────────────────────────────────

def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI via exponential moving average."""
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series]:
    """Standard MACD: returns (macd_line, signal_line)."""
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


# ─────────────────────────────────────────────────────────────────────────────
# Signal Classification
# ─────────────────────────────────────────────────────────────────────────────

def get_rsi_status(rsi: float) -> tuple[str, str]:
    if pd.isna(rsi): return "N/A",       ""
    if rsi > 70:     return "Overbought", "🔴"
    if rsi < 30:     return "Oversold",   "🟢"
    return "Neutral", "⚪"


def get_macd_status(
    macd: float, signal: float, prev_macd: float, prev_signal: float
) -> tuple[str, str]:
    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]):
        return "N/A", ""
    if (prev_macd <= prev_signal) and (macd > signal): return "Golden Cross", "🟢"
    if (prev_macd >= prev_signal) and (macd < signal): return "Death Cross",  "🔴"
    return "Steady", "⚪"


def get_recommendation(rsi_status: str, macd_status: str) -> tuple[str, str]:
    if rsi_status == "Oversold"   and macd_status == "Golden Cross": return "STRONG BUY",  "🚀"
    if macd_status == "Golden Cross":                                  return "BUY",          "✅"
    if rsi_status == "Overbought" and macd_status == "Death Cross":  return "STRONG SELL", "🔥"
    if macd_status == "Death Cross":                                   return "SELL",         "❌"
    return "WAIT", "⏳"


# ─────────────────────────────────────────────────────────────────────────────
# Market Detection
# ─────────────────────────────────────────────────────────────────────────────

def get_market(ticker: str) -> tuple[str, str]:
    parts = ticker.upper().split(".")
    if len(parts) > 1:
        return MARKET_MAP.get(parts[-1], ("🌐", f"Other ({parts[-1]})"))
    return ("🇺🇸", "US (NYSE / NASDAQ)")


# ─────────────────────────────────────────────────────────────────────────────
# Fibonacci Retracement & Extension
# ─────────────────────────────────────────────────────────────────────────────

def calc_fibonacci(
    high_s: pd.Series, low_s: pd.Series, price: float, lookback: int = 50
) -> dict:
    """Compute nearest Fibonacci resistance & support, upside/downside %, and R/R."""
    swing_high = float(high_s.tail(lookback).max())
    swing_low  = float(low_s.tail(lookback).min())
    diff       = swing_high - swing_low
    price      = float(price)

    # Retracement levels from high down + extension levels below low
    levels = sorted(set(
        [round(swing_high - r * diff, 4) for r in FIB_LEVELS]
        + [round(swing_low - (r - 1.0) * diff, 4) for r in [1.272, 1.618]]
    ))

    buf    = price * 0.002                              # 0.2 % buffer – avoids landing exactly on a level
    above  = [lvl for lvl in levels if lvl > price + buf]
    below  = [lvl for lvl in levels if lvl < price - buf]

    resist  = min(above) if above else round(swing_high * 1.05, 4)
    support = max(below) if below else round(swing_low  * 0.95, 4)

    upside_pct   = round((resist  - price) / price * 100, 1)
    downside_pct = round((price - support) / price * 100, 1)
    rr           = round(upside_pct / downside_pct, 2) if downside_pct > 0 else 0.0

    fib_label_map = {
        round(swing_high - r * diff, 4): f"{int(r * 100) if r in [0, 1] else r * 100:.1f}%"
        for r in FIB_LEVELS
    }
    resist_label  = fib_label_map.get(resist,  "Ext")
    support_label = fib_label_map.get(support, "Ext")

    return {
        "fib_resist":      resist,
        "fib_support":     support,
        "fib_resist_lbl":  resist_label,
        "fib_support_lbl": support_label,
        "upside_pct":      upside_pct,
        "downside_pct":    downside_pct,
        "rr":              rr,
        "swing_high":      round(swing_high, 2),
        "swing_low":       round(swing_low,  2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Analysis Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def analyze_ticker(
    ticker: str,
    rsi_period: int  = 14,
    macd_fast:  int  = 12,
    macd_slow:  int  = 26,
    macd_signal: int = 9,
    interval: str    = "1d",
    dl_period: str   = "6mo",
    timeframe_label: str = "Daily",
) -> dict | None:
    """Download OHLCV data and compute RSI / MACD / Fibonacci signals.

    Returns a result dict with underscore-keyed fields (safe for JSON
    serialisation) plus:
      ``_rec_key``      – raw recommendation string without emoji, for
                          reliable programmatic filtering (e.g. "STRONG BUY").
      ``_market_key``   – market name string for grouping.
      ``_market_label`` – emoji + market name for display headings.

    Returns ``None`` when fewer than 50 bars of data are available.
    """
    try:
        df = yf.download(
            ticker, period=dl_period, interval=interval,
            progress=False, auto_adjust=True,
        )
        if df is None or len(df) < 50:
            return None

        # Flatten MultiIndex columns produced by newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.dropna(inplace=True)

        close = df["Close"]
        high  = df["High"]
        low   = df["Low"]

        rsi_series             = calc_rsi(close, period=rsi_period)
        macd_line, signal_line = calc_macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)

        rsi        = float(rsi_series.iloc[-1])
        macd_val   = float(macd_line.iloc[-1])
        signal_val = float(signal_line.iloc[-1])
        prev_macd  = float(macd_line.iloc[-2])
        prev_sig   = float(signal_line.iloc[-2])
        price      = float(close.iloc[-1])
        price_date = df.index[-1].strftime("%Y-%m-%d")

        rsi_status,  rsi_icon  = get_rsi_status(rsi)
        macd_status, macd_icon = get_macd_status(macd_val, signal_val, prev_macd, prev_sig)
        rec,         rec_icon  = get_recommendation(rsi_status, macd_status)
        flag,        mkt_name  = get_market(ticker)
        fib                    = calc_fibonacci(high, low, price)

        return {
            # Private keys (prefix _) for grouping and reliable filtering
            "_market_key":    mkt_name,
            "_market_label":  f"{flag} {mkt_name}",
            "_rec_key":       rec,                  # e.g. "STRONG BUY" | "BUY" | "SELL" | "STRONG SELL" | "WAIT"
            # Public display fields
            "Ticker":         ticker.upper(),
            "Price":          round(price, 2),
            "PriceDate":      price_date,
            "RSI":            round(rsi, 1) if not pd.isna(rsi) else "N/A",
            "RSI_Status":     f"{rsi_icon} {rsi_status}",
            "MACD_Status":    f"{macd_icon} {macd_status}",
            "Recommendation": f"{rec_icon} {rec}",
            "Fib_Resist":     f"{fib['fib_resist']} ({fib['fib_resist_lbl']})",
            "Fib_Support":    f"{fib['fib_support']} ({fib['fib_support_lbl']})",
            "Upside":         f"+{fib['upside_pct']}%",
            "Downside":       f"-{fib['downside_pct']}%",
            "RR":             fib["rr"],
        }

    except Exception as e:
        flag, mkt_name = get_market(ticker)
        return {
            "_market_key":    mkt_name,
            "_market_label":  f"{flag} {mkt_name}",
            "_rec_key":       "ERROR",
            "Ticker":         ticker.upper(),
            "Price":          "Error",
            "PriceDate":      "-",
            "RSI":            "-",
            "RSI_Status":     "-",
            "MACD_Status":    "-",
            "Recommendation": str(e)[:60],
            "Fib_Resist":     "-",
            "Fib_Support":    "-",
            "Upside":         "-",
            "Downside":       "-",
            "RR":             "-",
        }
