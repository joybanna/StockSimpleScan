import re
import streamlit as st
import pandas as pd

from core import (
    DEFAULT_TICKERS, PRESETS, MARKET_MAP,
    analyze_ticker,
)

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

/* ── Legend grid ── */
.legend-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.5rem; }
.legend-block { background: #FAF8F5; border: 1.5px solid #E8E0D8; border-radius: 10px; padding: 0.75rem 1rem; }
.legend-title { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #8B7355; margin-bottom: 0.4rem; }
.legend-row { display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.15rem 0; border-bottom: 1px solid #F0EBE3; }
.legend-row:last-child { border-bottom: none; }
.legend-key { color: #6B5E54; font-weight: 500; }
.legend-val { color: #9C8E83; text-align: right; max-width: 60%; }
.rr-example { margin-top: 0.5rem; background: #F5F0E8; border-radius: 8px; padding: 0.5rem 0.75rem; font-size: 0.78rem; color: #6B5E54; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Constants (UI-only)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_TICKERS_STR = ", ".join(DEFAULT_TICKERS)

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
# Caching wrapper — results are cached per unique argument set for 5 minutes
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def cached_analyze_ticker(
    ticker: str,
    rsi_period: int,
    macd_fast: int,
    macd_slow: int,
    macd_signal: int,
    interval: str,
    dl_period: str,
    timeframe_label: str,
) -> dict | None:
    """Thin cache wrapper around core.analyze_ticker (5-minute TTL)."""
    return analyze_ticker(
        ticker, rsi_period, macd_fast, macd_slow, macd_signal,
        interval, dl_period, timeframe_label,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def to_display_row(r: dict, rsi_col: str) -> dict:
    """Remap underscore-keyed core result to Streamlit DataFrame column names."""
    return {
        "Ticker":         r["Ticker"],
        "Price":          r["Price"],
        "Price Date":     r["PriceDate"],
        rsi_col:          r["RSI"],
        "RSI Status":     r["RSI_Status"],
        "MACD Status":    r["MACD_Status"],
        "Recommendation": r["Recommendation"],
        "Fib Resist":     r["Fib_Resist"],
        "Fib Support":    r["Fib_Support"],
        "Upside %":       r["Upside"],
        "Downside %":     r["Downside"],
        "R/R":            r["RR"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Import helpers (Streamlit-specific)
# ─────────────────────────────────────────────────────────────────────────────

def sheet_url_to_csv(url: str) -> str | None:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        return None
    sheet_id = m.group(1)
    gid = (re.search(r"gid=(\d+)", url) or type("", (), {"group": lambda s, n: "0"})()).group(1)
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
st.markdown('<p style="color:#9C8E83;font-size:0.83rem;margin-top:-0.5rem">RSI &amp; MACD signals · powered by Yahoo Finance</p>', unsafe_allow_html=True)
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
        raw = st.text_input("Tickers", value=DEFAULT_TICKERS_STR,
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
    RSI period <b>{p['rsi']}</b> &nbsp;·&nbsp; MACD <b>{p['fast']}/{p['slow']}/{p['signal']}</b><br>
    Fibonacci: swing high/low 50 candles · levels 0–161.8%
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# UI — Legend
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("📖 How to read the results"):
    st.markdown("""
<div class="legend-grid">

<div class="legend-block">
<div class="legend-title">RSI (Relative Strength Index)</div>
<div class="legend-row"><span class="legend-key">🔴 Overbought</span><span class="legend-val">RSI &gt; 70 · ราคาสูงเกินไป อาจปรับตัวลง</span></div>
<div class="legend-row"><span class="legend-key">🟢 Oversold</span><span class="legend-val">RSI &lt; 30 · ราคาต่ำเกินไป อาจเด้งกลับ</span></div>
<div class="legend-row"><span class="legend-key">⚪ Neutral</span><span class="legend-val">RSI 30–70 · ยังไม่มีสัญญาณชัดเจน</span></div>
</div>

<div class="legend-block">
<div class="legend-title">MACD</div>
<div class="legend-row"><span class="legend-key">🟢 Golden Cross</span><span class="legend-val">MACD ตัด Signal ขึ้น · สัญญาณซื้อ</span></div>
<div class="legend-row"><span class="legend-key">🔴 Death Cross</span><span class="legend-val">MACD ตัด Signal ลง · สัญญาณขาย</span></div>
<div class="legend-row"><span class="legend-key">⚪ Steady</span><span class="legend-val">ไม่มี Crossover · รอสัญญาณ</span></div>
</div>

<div class="legend-block">
<div class="legend-title">Recommendation</div>
<div class="legend-row"><span class="legend-key">🚀 Strong Buy</span><span class="legend-val">RSI Oversold + MACD Golden Cross</span></div>
<div class="legend-row"><span class="legend-key">✅ Buy</span><span class="legend-val">MACD Golden Cross เท่านั้น</span></div>
<div class="legend-row"><span class="legend-key">⏳ Wait</span><span class="legend-val">ยังไม่มีสัญญาณชัดเจน</span></div>
<div class="legend-row"><span class="legend-key">❌ Sell</span><span class="legend-val">MACD Death Cross เท่านั้น</span></div>
<div class="legend-row"><span class="legend-key">🔥 Strong Sell</span><span class="legend-val">RSI Overbought + MACD Death Cross</span></div>
</div>

<div class="legend-block">
<div class="legend-title">Fibonacci &amp; R/R</div>
<div class="legend-row"><span class="legend-key">Fib Resist</span><span class="legend-val">ระดับต้านใกล้สุด (Upside target)</span></div>
<div class="legend-row"><span class="legend-key">Fib Support</span><span class="legend-val">ระดับรับใกล้สุด (Downside risk)</span></div>
<div class="legend-row"><span class="legend-key">Upside %</span><span class="legend-val">% กำไรถ้าราคาถึง Fib Resist</span></div>
<div class="legend-row"><span class="legend-key">Downside %</span><span class="legend-val">% ขาดทุนถ้าราคาถึง Fib Support</span></div>
<div class="legend-row"><span class="legend-key">R/R</span><span class="legend-val">Upside ÷ Downside · &gt; 1.0 คุ้มค่า</span></div>
<div class="rr-example">
<b>ตัวอย่าง R/R = 2.0</b><br>
ราคา 100 · Resist 108 (+8%) · Support 104 (-4%)<br>
R/R = 8 ÷ 4 = <b>2.0</b> → ถูก ได้ 2 บาท / ผิด เสีย 1 บาท
</div>
</div>

</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# UI — Scan button
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("")
scan_btn = st.button("Scan ▶", type="primary", disabled=not tickers_ready, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────

if scan_btn and tickers_ready:
    results: list[dict] = []
    progress = st.progress(0, text="")
    for i, ticker in enumerate(tickers_ready):
        progress.progress((i + 1) / len(tickers_ready), text=f"Scanning {ticker}…")
        row = cached_analyze_ticker(
            ticker,
            rsi_period=p["rsi"], macd_fast=p["fast"], macd_slow=p["slow"], macd_signal=p["signal"],
            interval=p["interval"], dl_period=p["dl_period"], timeframe_label=p["label"],
        )
        if row:
            results.append(row)
    progress.empty()

    if results:
        rsi_col      = f"RSI ({p['rsi']}·{p['label']})"
        display_cols = [
            "Ticker", "Price", "Price Date",
            rsi_col, "RSI Status", "MACD Status", "Recommendation",
            "Fib Resist", "Fib Support", "Upside %", "Downside %", "R/R",
        ]

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
            rows = [to_display_row(r, rsi_col) for r in groups[label]]
            st.dataframe(pd.DataFrame(rows)[display_cols], use_container_width=True, hide_index=True)
            st.markdown("")

        # ── Summary metrics (uses _rec_key for reliable filtering) ──
        st.markdown("---")
        strong_buy  = [r["Ticker"] for r in results if r["_rec_key"] == "STRONG BUY"]
        buy         = [r["Ticker"] for r in results if r["_rec_key"] == "BUY"]
        sell        = [r["Ticker"] for r in results if r["_rec_key"] == "SELL"]
        strong_sell = [r["Ticker"] for r in results if r["_rec_key"] == "STRONG SELL"]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🚀 Strong Buy", len(strong_buy))
            if strong_buy: st.caption(", ".join(strong_buy))
        with c2:
            st.metric("✅ Buy", len(buy))
            if buy: st.caption(", ".join(buy))
        with c3:
            st.metric("❌ Sell", len(sell))
            if sell: st.caption(", ".join(sell))
        with c4:
            st.metric("🔥 Strong Sell", len(strong_sell))
            if strong_sell: st.caption(", ".join(strong_sell))
    else:
        st.warning("No data returned — check ticker symbols and try again.")
