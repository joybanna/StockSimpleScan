# 📈 Stock Scanner

A minimal web dashboard for scanning RSI & MACD signals across multiple stocks and markets — powered by Yahoo Finance.

**Live demo:** [share.streamlit.io](https://share.streamlit.io) *(deploy your own below)*

---

## Features

- **Multi-market support** — US, Thailand (.BK), Hong Kong (.HK), Japan (.T), Singapore (.SI), London (.L), Australia (.AX), and more
- **Grouped results** — table separated by market (US first, Thailand second, rest alphabetically)
- **3 timeframe presets** — Day (1d), Week (1wk), Month (1mo) with appropriate lookback periods
- **RSI** — period 14, status: Overbought / Oversold / Neutral
- **MACD** — 12/26/9, status: Golden Cross / Death Cross / Steady
- **Recommendation** — combined signal: Strong Buy / Buy / Wait / Sell / Strong Sell
- **3 ticker input modes** — Manual text, Google Sheet, or CSV/Excel upload
- **Price Date** — shows the exact trading date of the displayed price

---

## Recommendation Logic

| Signal | Condition |
|---|---|
| 🚀 Strong Buy | RSI Oversold **+** MACD Golden Cross |
| ✅ Buy | MACD Golden Cross only |
| ⏳ Wait | No clear signal |
| ❌ Sell | MACD Death Cross only |
| 🔥 Strong Sell | RSI Overbought **+** MACD Death Cross |

---

## Timeframe Presets

| Preset | Candle | Lookback | RSI | MACD |
|---|---|---|---|---|
| 📅 Day | `1d` | 6 months | 14 | 12/26/9 |
| 📆 Week | `1wk` | 2 years | 14 | 12/26/9 |
| 🗓️ Month | `1mo` | 5 years | 14 | 12/26/9 |

---

## Ticker Format

| Market | Pattern | Example |
|---|---|---|
| 🇺🇸 US (NYSE / NASDAQ) | `SYMBOL` | `AAPL`, `NVDA`, `MSFT` |
| 🇹🇭 Thailand (SET) | `SYMBOL.BK` | `PTT.BK`, `AOT.BK` |
| 🇭🇰 Hong Kong (HKEX) | `SYMBOL.HK` | `0700.HK` |
| 🇯🇵 Japan (TSE) | `SYMBOL.T` | `7203.T` |
| 🇸🇬 Singapore (SGX) | `SYMBOL.SI` | `D05.SI` |
| 🇬🇧 London (LSE) | `SYMBOL.L` | `SHEL.L` |
| 🇦🇺 Australia (ASX) | `SYMBOL.AX` | `CBA.AX` |

---

## Import Tickers

**Manual** — type tickers separated by commas
```
AAPL, NVDA, PTT.BK, ADVANC.BK
```

**Google Sheet** — paste a public sheet URL
- Put one ticker per row in **column A** (no header needed)
- Share the sheet: *File → Share → Anyone with the link → Viewer*

**CSV / Excel** — upload a `.csv`, `.xlsx`, or `.xls` file
- One ticker per row in column A
- Header row is optional

---

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run
streamlit run app.py
```

---

## Deploy on Streamlit Cloud (Free)

1. Fork or push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub → **New app**
4. Select repo → Main file: `app.py` → **Deploy**

> Private repos: authorize Streamlit Cloud to access private repos during step 3.

---

## Stack

- [Streamlit](https://streamlit.io) — UI framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [pandas](https://pandas.pydata.org) — data processing & indicator calculations
