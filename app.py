import re
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Scanner", layout="centered", page_icon="📈")

st.markdown("""
<style>
/* ── Page ── */
html, body, [data-testid="stAppViewContainer"] { background-color: #FAF8F5; }
[data-testid="stAppViewContainer"] > .main { padding-top: 2rem; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Typography ── */
p, label, div { color: #2D2520; }

/* ── Card ── */
.card {
    background: #FFFCF9;
    border: 1.5px solid #E8E0D8;
    border-radius: 16px;
    padding: 1.25rem 1.5rem 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 10px rgba(45,37,32,0.05);
}
.card-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9C8E83;
    margin-bottom: 0.5rem;
}
.hint { color: #B0A399; font-size: 0.78rem; line-height: 1.5; margin-top: 0.35rem; }

/* ── Radio pills ── */
div[role="radiogroup"] { gap: 0.4rem; flex-wrap: wrap; }
div[role="radiogroup"] label {
    background: #F0EBE3;
    border: 1.5px solid #DDD5CC;
    border-radius: 20px;
    padding: 0.3rem 0.9rem;
    font-size: 0.83rem;
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
    background: #FAF8F5 !important;
    padding: 0.45rem 0.85rem !important;
    font-size: 0.88rem !important;
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
    padding: 0.55rem 2rem !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    width: 100%;
    transition: background 0.15s ease;
}
[data-testid="stButton"] > button:hover { background: #7A6347 !important; }
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

/* ── Alerts & uploader ── */
[data-testid="stAlert"], [data-testid="stFileUploader"] { border-radius: 10px; border: none; }

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1.5px solid #E8E0D8 !important;
    border-radius: 10px !important;
    background: #FAF8F5 !important;
}

/* ── Divider ── */
hr { border-color: #E8E0D8; margin: 1.25rem 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Constants & presets
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TICKERS = "AAPL, NVDA, MSFT, PTT.BK, ADVANC.BK, AOT.BK"

PRESETS = {
    "Day":   {"interval": "1d",  "dl_period": "6mo", "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Daily"},
    "Week":  {"interval": "1wk", "dl_period": "2y",  "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Weekly"},
    "Month": {"interval": "1mo", "dl_period": "5y",  "rsi": 14, "fast": 12, "slow": 26, "signal": 9, "label": "Monthly"},
}

MARKET_MAP = {
    "BK": ("🇹🇭", "Thailand (SET)"),   "HK": ("🇭🇰", "Hong Kong (HKEX)"),
    "L":  ("🇬🇧", "London (LSE)"),     "T":  ("🇯🇵", "Japan (TSE)"),
    "SI": ("🇸🇬", "Singapore (SGX)"),  "AX": ("🇦🇺", "Australia (ASX)"),
    "KS": ("🇰🇷", "South Korea (KRX)"), "SS": ("🇨🇳", "China (Shanghai)"),
    "SZ": ("🇨🇳", "China (Shenzhen)"), "NS": ("🇮🇳", "India (NSE)"),
    "BO": ("🇮🇳", "India (BSE)"),      "PA": ("🇫🇷", "France (Euronext)"),
    "DE": ("🇩🇪", "Germany (XETRA)"),  "TW": ("🇹🇼", "Taiwan (TWSE)"),
}

TICKER_HELP = """
| Market | Pattern | Example |
|---|---|---|
| 🇺🇸 US | `SYMBOL` | `AAPL`, `NVDA` |
| 🇹🇭 Thailand | `SYMBOL.BK` | `PTT.BK` |
| 🇭🇰 Hong Kong | `SYMBOL.HK` | `0700.HK` |
| 🇯🇵 Japan | `SYMBOL.T` | `7203.T` |
| 🇸🇬 Singapore | `SYMBOL.SI` | `D05.SI` |
| 🇬🇧 London | `SYMBOL.L` | `SHEL.L` |
| 🇦🇺 Australia | `SYMBOL.AX` | `CBA.AX` |
"""


# ─────────────────────────────────────────────────────────────────────────────
# Indicator calculations
# ─────────────────────────────────────────────────────────────────────────────

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
    if pd.isna(rsi): return "N/A", ""
    if rsi > 70:     return "Overbought", "🔴"
    if rsi < 30:     return "Oversold",   "🟢"
    return "Neutral", "⚪"


def get_macd_status(macd, signal, prev_macd, prev_signal):
    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]): return "N/A", ""
    if (prev_macd <= prev_signal) and (macd > signal): return "Golden Cross", "🟢"
    if (prev_macd >= prev_signal) and (macd < signal): return "Death Cross",  "🔴"
    return "Steady", "⚪"


def get_recommendation(rsi_status, macd_status):
    if rsi_status == "Oversold"   and macd_status == "Golden Cross": return "STRONG BUY",  "🚀"
    if macd_status == "Golden Cross":                                 return "BUY",          "✅"
    if rsi_status == "Overbought" and macd_status == "Death Cross":  return "STRONG SELL", "🔥"
    if macd_status == "Death Cross":                                  return "SELL",         "❌"
    return "WAIT", "⏳"


def get_market(ticker: str) -> tuple[str, str]:
    parts = ticker.upper().split(".")
    if len(parts) > 1:
        return MARKET_MAP.get(parts[-1], ("🌐", f"Other ({parts[-1]})"))
    return ("🇺🇸", "US (NYSE / NASDAQ)")


def analyze_ticker(ticker, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9,
                   interval="1d", dl_period="6mo", timeframe_label="Daily"):
    try:
        df = yf.download(ticker, period=dl_period, interval=interval, progress=False, auto_adjust=True)
        if df is None or len(df) < 50:
            return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.dropna(inplace=True)

        close = df["Close"]
        rsi_series = calc_rsi(close, period=rsi_period)
        macd_line, signal_line = calc_macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)

        rsi      = rsi_series.iloc[-1]
        macd     = macd_line.iloc[-1]
        signal   = signal_line.iloc[-1]
        prev_macd, prev_signal = macd_line.iloc[-2], signal_line.iloc[-2]
        price    = close.iloc[-1]
        price_date = df.index[-1].strftime("%Y-%m-%d")

        rsi_status, rsi_icon   = get_rsi_status(rsi)
        macd_status, macd_icon = get_macd_status(macd, signal, prev_macd, prev_signal)
        rec, rec_icon          = get_recommendation(rsi_status, macd_status)
        flag, market_name      = get_market(ticker)

        return {
            "_market_key":   market_name,
            "_market_label": f"{flag} {market_name}",
            "Ticker":        ticker.upper(),
            "Price":         round(float(price), 2),
            "Price Date":    price_date,
            f"RSI ({rsi_period}·{timeframe_label})": round(float(rsi), 1) if not pd.isna(rsi) else "N/A",
            "RSI Status":    f"{rsi_icon} {rsi_status}",
            "MACD Status":   f"{macd_icon} {macd_status}",
            "Recommendation": f"{rec_icon} {rec}",
        }
    except Exception as e:
        flag, market_name = get_market(ticker)
        rsi_col = f"RSI ({rsi_period}·{timeframe_label})"
        return {"_market_key": market_name, "_market_label": f"{flag} {market_name}",
                "Ticker": ticker.upper(), "Price": "Error", "Price Date": "-",
                rsi_col: "-", "RSI Status": "-", "MACD Status": "-",
                "Recommendation": str(e)[:40]}


# ─────────────────────────────────────────────────────────────────────────────
# Import helpers
# ─────────────────────────────────────────────────────────────────────────────

def sheet_url_to_csv(url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m: return None
    sheet_id = m.group(1)
    gid = (re.search(r"gid=(\d+)", url) or type("", (), {"group": lambda s, n: "0"})()).group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def load_tickers_from_sheet(url: str) -> list[str] | None:
    csv_url = sheet_url_to_csv(url)
    if not csv_url: return None
    try:
        df = pd.read_csv(csv_url, header=None)
        tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        return [t for t in tickers if t and not t.lower().startswith("ticker")]
    except Exception:
        return None


def load_tickers_from_file(f) -> list[str]:
    try:
        df = pd.read_csv(f, header=None) if f.name.endswith(".csv") else pd.read_excel(f, header=None)
        tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        return [t for t in tickers if t and not t.lower().startswith("ticker")]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# UI — Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Stock Scanner")
st.markdown('<p style="color:#9C8E83;font-size:0.83rem;margin-top:-0.5rem">RSI & MACD signals · powered by Yahoo Finance</p>', unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# UI — Config card (2 columns)
# ─────────────────────────────────────────────────────────────────────────────

left, right = st.columns([3, 2], gap="large")
tickers_ready: list[str] = []

with left:
    st.markdown('<div class="card-label">Tickers</div>', unsafe_allow_html=True)
    input_mode = st.radio("Source", ["Manual", "Google Sheet", "Upload File"],
                          horizontal=True, label_visibility="collapsed")

    if input_mode == "Manual":
        raw = st.text_input("Tickers", value=DEFAULT_TICKERS,
                            placeholder="e.g. AAPL, NVDA, PTT.BK", label_visibility="collapsed")
        tickers_ready = [t.strip().upper() for t in raw.split(",") if t.strip()]

    elif input_mode == "Google Sheet":
        url = st.text_input("Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...",
                            label_visibility="collapsed")
        if url:
            loaded = load_tickers_from_sheet(url)
            if loaded:
                tickers_ready = loaded
                st.success(f"{len(tickers_ready)} tickers loaded")
            else:
                st.error("Cannot read sheet — check URL and sharing settings.")

    elif input_mode == "Upload File":
        uploaded = st.file_uploader("File", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
        if uploaded:
            tickers_ready = load_tickers_from_file(uploaded)
            if tickers_ready:
                st.success(f"{len(tickers_ready)} tickers loaded")
            else:
                st.error("Cannot read tickers — ensure tickers are in column A.")

    with st.expander("ℹ️ Ticker format"):
        st.markdown(TICKER_HELP)
        if input_mode == "Google Sheet":
            st.markdown("**Sheet:** tickers in column A · share as *Anyone with link → Viewer*")
        elif input_mode == "Upload File":
            st.markdown("**File:** one ticker per row in column A · header optional")

with right:
    st.markdown('<div class="card-label">Timeframe</div>', unsafe_allow_html=True)
    preset_choice = st.radio(
        "Timeframe", list(PRESETS.keys()), horizontal=True,
        label_visibility="collapsed",
        format_func=lambda x: {"Day": "📅 Day", "Week": "📆 Week", "Month": "🗓️ Month"}[x],
    )
    p = PRESETS[preset_choice]

    st.markdown(f"""<div class="hint">
    Candle &nbsp;<b>{p['label']}</b> &nbsp;·&nbsp; Lookback <b>{p['dl_period']}</b><br>
    RSI period <b>{p['rsi']}</b> &nbsp;·&nbsp; MACD <b>{p['fast']}/{p['slow']}/{p['signal']}</b>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# UI — Scan button
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("")
scan_btn = st.button("Scan ▶", type="primary", disabled=not tickers_ready, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────

if scan_btn and tickers_ready:
    results = []
    progress = st.progress(0, text="")
    for i, ticker in enumerate(tickers_ready):
        progress.progress((i + 1) / len(tickers_ready), text=f"Scanning {ticker}…")
        row = analyze_ticker(
            ticker,
            rsi_period=p["rsi"], macd_fast=p["fast"], macd_slow=p["slow"], macd_signal=p["signal"],
            interval=p["interval"], dl_period=p["dl_period"], timeframe_label=p["label"],
        )
        if row:
            results.append(row)
    progress.empty()

    if results:
        rsi_col      = f"RSI ({p['rsi']}·{p['label']})"
        display_cols = ["Ticker", "Price", "Price Date", rsi_col, "RSI Status", "MACD Status", "Recommendation"]

        def market_sort_key(label: str) -> tuple:
            if "US "      in label: return (0, label)
            if "Thailand" in label: return (1, label)
            return (2, label)

        groups: dict[str, list] = {}
        for r in results:
            groups.setdefault(r["_market_label"], []).append(r)

        st.markdown("---")
        for label in sorted(groups.keys(), key=market_sort_key):
            st.markdown(f"#### {label}")
            rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in groups[label]]
            st.dataframe(pd.DataFrame(rows)[display_cols], use_container_width=True, hide_index=True)
            st.markdown("")

        # Summary
        st.markdown("---")
        strong_buy  = [r["Ticker"] for r in results if "STRONG BUY"  in r["Recommendation"]]
        buy         = [r["Ticker"] for r in results if r["Recommendation"].endswith("BUY") and "STRONG" not in r["Recommendation"]]
        strong_sell = [r["Ticker"] for r in results if "STRONG SELL" in r["Recommendation"]]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Strong Buy", len(strong_buy))
            if strong_buy: st.caption(", ".join(strong_buy))
        with c2:
            st.metric("Buy", len(buy))
            if buy: st.caption(", ".join(buy))
        with c3:
            st.metric("Strong Sell", len(strong_sell))
            if strong_sell: st.caption(", ".join(strong_sell))
    else:
        st.warning("No data returned — check ticker symbols and try again.")
