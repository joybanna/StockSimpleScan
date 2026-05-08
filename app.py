import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Signal Scanner", layout="wide")
st.title("Stock Signal Scanner")
st.caption("Scan RSI & MACD signals via Yahoo Finance")

DEFAULT_TICKERS = "AAPL, NVDA, MSFT, PTT.BK, ADVANC.BK, AOT.BK"

ticker_input = st.text_input(
    "Enter tickers (comma-separated):",
    value=DEFAULT_TICKERS,
    placeholder="e.g. AAPL, NVDA, PTT.BK"
)

scan_btn = st.button("Scan", type="primary")


def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def get_rsi_status(rsi):
    if pd.isna(rsi):
        return "N/A", ""
    if rsi > 70:
        return "Overbought", "🔴"
    if rsi < 30:
        return "Oversold", "🟢"
    return "Neutral", "⚪"


def get_macd_status(macd, signal, prev_macd, prev_signal):
    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]):
        return "N/A", ""
    if (prev_macd <= prev_signal) and (macd > signal):
        return "Golden Cross", "🟢"
    if (prev_macd >= prev_signal) and (macd < signal):
        return "Death Cross", "🔴"
    return "Steady", "⚪"


def get_recommendation(rsi_status, macd_status):
    if rsi_status == "Oversold" and macd_status == "Golden Cross":
        return "STRONG BUY", "🚀"
    if macd_status == "Golden Cross":
        return "BUY", "✅"
    if rsi_status == "Overbought" and macd_status == "Death Cross":
        return "STRONG SELL", "🔥"
    if macd_status == "Death Cross":
        return "SELL", "❌"
    return "WAIT", "⏳"


def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 50:
            return None

        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)

        close = df["Close"]
        rsi_series = calc_rsi(close)
        macd_line, signal_line = calc_macd(close)

        rsi = rsi_series.iloc[-1]
        macd = macd_line.iloc[-1]
        signal = signal_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        price = close.iloc[-1]

        rsi_status, rsi_icon = get_rsi_status(rsi)
        macd_status, macd_icon = get_macd_status(macd, signal, prev_macd, prev_signal)
        rec, rec_icon = get_recommendation(rsi_status, macd_status)

        return {
            "Ticker": ticker.upper(),
            "Price": round(float(price), 2),
            "RSI": round(float(rsi), 1) if not pd.isna(rsi) else "N/A",
            "RSI Status": f"{rsi_icon} {rsi_status}",
            "MACD Status": f"{macd_icon} {macd_status}",
            "Recommendation": f"{rec_icon} {rec}",
        }
    except Exception as e:
        return {"Ticker": ticker.upper(), "Price": "Error", "RSI": "-", "RSI Status": "-", "MACD Status": "-", "Recommendation": str(e)[:40]}


if scan_btn and ticker_input.strip():
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    results = []

    progress = st.progress(0, text="Fetching data...")
    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / len(tickers), text=f"Analyzing {ticker}...")
        row = analyze_ticker(ticker)
        if row:
            results.append(row)

    progress.empty()

    if results:
        df_result = pd.DataFrame(results)
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        strong_buy = [r["Ticker"] for r in results if "STRONG BUY" in r["Recommendation"]]
        buy = [r["Ticker"] for r in results if r["Recommendation"].endswith("BUY") and "STRONG" not in r["Recommendation"]]
        strong_sell = [r["Ticker"] for r in results if "STRONG SELL" in r["Recommendation"]]

        cols = st.columns(3)
        with cols[0]:
            st.metric("Strong Buy", len(strong_buy))
            if strong_buy:
                st.caption(", ".join(strong_buy))
        with cols[1]:
            st.metric("Buy", len(buy))
            if buy:
                st.caption(", ".join(buy))
        with cols[2]:
            st.metric("Strong Sell", len(strong_sell))
            if strong_sell:
                st.caption(", ".join(strong_sell))
    else:
        st.warning("No data returned. Check ticker symbols and try again.")
