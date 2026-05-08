import re
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Scanner", layout="centered", page_icon="📈")

st.markdown("""
<style>
/* ── Page ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #FAF8F5;
}
[data-testid="stAppViewContainer"] > .main {
    padding-top: 2rem;
}

/* ── Hide toolbar clutter ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Typography ── */
h1 { font-size: 1.6rem !important; font-weight: 600 !important; color: #2D2520 !important; letter-spacing: -0.3px; }
p, label, div { color: #2D2520; }
.caption { color: #9C8E83 !important; font-size: 0.82rem; }

/* ── Radio pills ── */
div[role="radiogroup"] {
    gap: 0.5rem;
    flex-wrap: wrap;
}
div[role="radiogroup"] label {
    background: #F0EBE3;
    border: 1.5px solid #DDD5CC;
    border-radius: 20px;
    padding: 0.35rem 1rem;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s ease;
    color: #6B5E54 !important;
}
div[role="radiogroup"] label:has(input:checked) {
    background: #8B7355;
    border-color: #8B7355;
    color: #FAF8F5 !important;
}

/* ── Input fields ── */
[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #DDD5CC !important;
    background: #FFFCF9 !important;
    padding: 0.5rem 0.85rem !important;
    font-size: 0.9rem !important;
    color: #2D2520 !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #8B7355 !important;
    box-shadow: 0 0 0 3px rgba(139,115,85,0.12) !important;
}

/* ── Scan button ── */
[data-testid="stButton"] > button {
    background: #8B7355 !important;
    color: #FAF8F5 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 2rem !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.2px;
    transition: background 0.15s ease;
}
[data-testid="stButton"] > button:hover {
    background: #7A6347 !important;
}
[data-testid="stButton"] > button:disabled {
    background: #DDD5CC !important;
    color: #A89B91 !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1.5px solid #E8E0D8;
    box-shadow: 0 2px 12px rgba(45,37,32,0.06);
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #FFFCF9;
    border: 1.5px solid #E8E0D8;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 8px rgba(45,37,32,0.05);
}
[data-testid="stMetricLabel"] { color: #9C8E83 !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #2D2520 !important; font-size: 1.5rem !important; font-weight: 600 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 10px;
    border: none;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border-radius: 10px;
}

/* ── Divider ── */
hr { border-color: #E8E0D8; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📈 Stock Scanner")
st.markdown('<p class="caption">RSI & MACD signals · powered by Yahoo Finance</p>', unsafe_allow_html=True)
st.markdown("---")

DEFAULT_TICKERS = "AAPL, NVDA, MSFT, PTT.BK, ADVANC.BK, AOT.BK"


# ── Indicator calculations ────────────────────────────────────────────────────

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


# ── Signal helpers ────────────────────────────────────────────────────────────

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


# ── Google Sheet / CSV import ─────────────────────────────────────────────────

def sheet_url_to_csv(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        return None
    sheet_id = match.group(1)
    gid_match = re.search(r"gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def load_tickers_from_sheet(url: str) -> list[str] | None:
    csv_url = sheet_url_to_csv(url)
    if not csv_url:
        return None
    try:
        df = pd.read_csv(csv_url, header=None)
        tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        return [t for t in tickers if t and not t.lower().startswith("ticker")]
    except Exception:
        return None


def load_tickers_from_file(uploaded_file) -> list[str]:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
        tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        return [t for t in tickers if t and not t.lower().startswith("ticker")]
    except Exception:
        return []


# ── Ticker input UI ───────────────────────────────────────────────────────────

input_mode = st.radio("Source", ["Manual", "Google Sheet", "Upload CSV / Excel"], horizontal=True, label_visibility="collapsed")

tickers_ready: list[str] = []

if input_mode == "Manual":
    ticker_input = st.text_input(
        "Tickers",
        value=DEFAULT_TICKERS,
        placeholder="e.g. AAPL, NVDA, PTT.BK",
        label_visibility="collapsed",
    )
    tickers_ready = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

elif input_mode == "Google Sheet":
    st.markdown('<p class="caption">Sheet must be shared as "Anyone with the link can view" · Tickers in column A</p>', unsafe_allow_html=True)
    sheet_url = st.text_input("Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...", label_visibility="collapsed")
    if sheet_url:
        loaded = load_tickers_from_sheet(sheet_url)
        if loaded:
            tickers_ready = loaded
            st.success(f"Loaded {len(tickers_ready)} tickers · {', '.join(tickers_ready[:8])}{'…' if len(tickers_ready) > 8 else ''}")
        else:
            st.error("Could not read sheet — check the URL and sharing settings.")

elif input_mode == "Upload CSV / Excel":
    st.markdown('<p class="caption">Tickers in column A · header optional</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
    if uploaded:
        tickers_ready = load_tickers_from_file(uploaded)
        if tickers_ready:
            st.success(f"Loaded {len(tickers_ready)} tickers · {', '.join(tickers_ready[:8])}{'…' if len(tickers_ready) > 8 else ''}")
        else:
            st.error("Could not read tickers — check that tickers are in column A.")

st.markdown("")
scan_btn = st.button("Scan", type="primary", disabled=not tickers_ready, use_container_width=False)

# ── Results ───────────────────────────────────────────────────────────────────

if scan_btn and tickers_ready:
    results = []

    progress = st.progress(0, text="")
    for i, ticker in enumerate(tickers_ready):
        progress.progress((i + 1) / len(tickers_ready), text=f"Scanning {ticker}…")
        row = analyze_ticker(ticker)
        if row:
            results.append(row)

    progress.empty()

    if results:
        st.markdown("---")
        df_result = pd.DataFrame(results)
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        st.markdown("")
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
        st.warning("No data returned — check ticker symbols and try again.")
