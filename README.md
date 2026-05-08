# Stock Signal Scanner

Web dashboard for scanning RSI & MACD signals via Yahoo Finance.

## Features
- Multi-ticker scan (US & Thai stocks e.g. `PTT.BK`)
- RSI(14) — Overbought / Oversold / Neutral
- MACD(12,26,9) — Golden Cross / Death Cross / Steady
- Recommendation: Strong Buy / Buy / Wait / Sell / Strong Sell

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo → select `app.py` → Deploy
