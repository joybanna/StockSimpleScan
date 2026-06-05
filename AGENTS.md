# AGENTS.md — Stock Scanner

> This file is intended for AI coding agents. It describes the project structure, build process, conventions, and everything else you need to know before touching code.

---

## Project Overview

**Stock Scanner** is a Python application that downloads historical stock price data from Yahoo Finance and calculates technical-indicator signals (RSI, MACD, Fibonacci retracement) to produce buy/sell recommendations. It supports stocks from multiple global markets — US, Thailand (SET), Hong Kong, Japan, Singapore, London, Australia, and others.

The project provides **two UI flavours** from the same backend logic:

1. **Streamlit web app** (`app.py`) — runs in a browser, useful for quick local demos or cloud deployment.
2. **Desktop application** (`desktop_app.py`) — a native-feeling Windows app built with `pywebview`, shipping a custom HTML/CSS/JS frontend (`ui/`).

The codebase is small, flat, and intentionally kept simple. There is no formal test suite, no CI/CD pipeline, and no packaging beyond a Windows batch launcher.

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Backend logic |
| Data source | `yfinance` | OHLCV data from Yahoo Finance |
| Data processing | `pandas` | Indicator calculations (RSI, MACD, Fibonacci) |
| Desktop shell | `pywebview` | Native window wrapping the HTML frontend |
| Web UI (desktop) | HTML5, Vanilla CSS3, Vanilla JS | Fluent-design dashboard with dark/light mode |
| Web UI (Streamlit) | Streamlit + inline CSS | Simpler browser-based UI |
| File I/O | `openpyxl`, `pandas` | Reading CSV/Excel ticker lists |
| HTTP | `requests` | Fetching public Google Sheets |

---

## Project Structure

```
StockSimpleScan/
├── app.py              # Streamlit entry point
├── desktop_app.py      # pywebview desktop entry point
├── core.py             # Shared analysis logic (indicators, constants, analyze_ticker)
├── requirements.txt    # Python dependencies
├── tickers.csv         # Default ticker list (Thai + US stocks)
├── run_app.bat         # Windows launcher: creates venv, installs deps, opens desktop app
├── ui/                 # Desktop-app frontend assets
│   ├── index.html      # Main layout (sidebar + dashboard + help modal)
│   ├── style.css       # CSS variables, dark/light themes, layout, animations
│   └── app.js          # State management, event handling, results rendering
├── .streamlit/
│   └── config.toml     # Streamlit theme colours and headless server flag
└── AGENTS.md           # This file
```

---

## How to Run

### Prerequisites

- Python 3.11 or newer installed and available on `PATH`.
- Windows is the primary target OS (the batch launcher uses Windows-specific commands).

### Desktop App (recommended)

Double-click **`run_app.bat`** in the project root. The script will:

1. Check for Python (if missing, opens the Microsoft Store page).
2. Create a virtual environment `.venv` if it does not exist.
3. Install/upgrade packages from `requirements.txt`.
4. Create a Desktop shortcut named **"Stock Scanner"** (once only).
5. Launch `desktop_app.py` via `pythonw.exe` (no console window).

To run manually without the batch file:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python desktop_app.py
```

### Streamlit App

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

---

## Build / Packaging Notes

There is **no formal build system** (no `pyproject.toml`, `setup.py`, `setup.cfg`, or `package.json`). Deployment relies entirely on:

- `requirements.txt` for dependency pinning.
- `run_app.bat` for first-time setup and shortcut creation.
- Source files being copied as-is (the desktop app loads `ui/index.html` from a relative path).

If you need to bundle the app for distribution, consider:

- **PyInstaller** or **Nuitka** to produce a single `.exe` that embeds Python, `ui/`, and all dependencies.
- Update `get_asset_path()` in `desktop_app.py` if the relative-path resolution changes after bundling.

---

## Code Organisation

### `core.py` — Shared Business Logic

This is the **single source of truth** for all technical analysis. Both `app.py` and `desktop_app.py` import from here.

Key pieces:

| Symbol | Description |
|---|---|
| `DEFAULT_TICKERS` | Hard-coded fallback list (Thai SET + US tech stocks). |
| `PRESETS` | Timeframe presets (`Day`, `Week`, `Month`) mapping to Yahoo-interval strings, lookback periods, and indicator parameters. |
| `MARKET_MAP` | Suffix-to-market mapping (e.g. `.BK` → Thailand, `.HK` → Hong Kong, no suffix → US). |
| `FIB_LEVELS` | Fibonacci ratios used for retracement/extension calculations. |
| `calc_rsi()` | Wilder’s RSI via exponential moving average. |
| `calc_macd()` | Standard MACD (EMA fast − EMA slow) + signal line. |
| `get_rsi_status()` / `get_macd_status()` / `get_recommendation()` | Classification helpers that return `(text, emoji)` tuples. |
| `calc_fibonacci()` | Nearest resistance/support from swing high/low over 50 bars, upside/downside %, and risk/reward ratio. |
| `analyze_ticker()` | **Main entry point.** Downloads data, runs all indicators, and returns a dict with display fields plus `_rec_key`, `_market_key`, and `_market_label` for reliable filtering/grouping. Returns `None` if fewer than 50 bars are available. |

> **Important:** `analyze_ticker()` handles `pd.MultiIndex` columns that newer `yfinance` versions produce. Do not remove that flattening logic.

### `app.py` — Streamlit UI

- Contains **UI-only constants** and **display helpers** (`to_display_row()`).
- `cached_analyze_ticker()` wraps `core.analyze_ticker()` with `@st.cache_data(ttl=300)` so repeated scans of the same ticker within 5 minutes are instant.
- Supports three ticker input modes: **Manual**, **Google Sheet**, **Upload File**.
- Groups results by market in the UI, with sorting: US first, Thailand second, everything else alphabetically.
- Uses custom inline CSS to override Streamlit’s default look (warm beige/gold palette).

### `desktop_app.py` — pywebview Bridge

- Defines `PyAPI`, the Python object exposed to JavaScript via `js_api`.
- Thread-safety: `_safe_eval_js()` holds a `threading.Lock()` around `window.evaluate_js()` because pywebview is not thread-safe for concurrent JS calls from worker threads.
- `scan_tickers()` uses `ThreadPoolExecutor(max_workers=min(8, total))` for parallel downloads and pushes live progress to the frontend after each ticker finishes.
- Native file dialog (`select_file()`) and Google Sheet fetching (`fetch_google_sheet()`) live here.

### `ui/` — Desktop Frontend

- `index.html` — semantic layout with three view states: **Welcome**, **Scanning**, **Results**.
- `style.css` — CSS custom properties for theming (`[data-theme="dark"]` and `[data-theme="light"]`). Dark mode is default.
- `app.js` —
  - State object (`appState`) tracks tickers, timeframe, theme, and results.
  - Persists theme and manual tickers to `localStorage`.
  - Listens for `pywebviewready` before attempting API calls.
  - `renderResults()` groups tables by market label and uses `_rec_key` (not the emoji string) for reliable badge colouring.

---

## Conventions & Style Guidelines

### Python

- **Type hints** are used for function signatures (`-> tuple[str, str]`, `-> dict | None`, etc.).
- **Docstrings** follow Google-style / plain descriptive style.
- Constants are `SCREAMING_SNAKE_CASE`.
- Functions use `snake_case`.
- Sections in large files are separated by ASCII-art comment banners (`# ──────────────────`).
- No linting configuration (no `.flake8`, `ruff.toml`, etc.) is present; keep code PEP-8-ish by eye.

### JavaScript / CSS

- Vanilla JS only — no build step, no bundler, no frameworks.
- CSS uses **custom properties** (`var(--bg-card)`) for everything colour-related so dark/light mode toggling is a single attribute change on `<html>`.
- Class naming is kebab-case (`state-container`, `metric-card`).

---

## Testing Strategy

**There is currently no test suite.** If you add one:

- Use the standard library `unittest` or `pytest` (not installed by default; add to `requirements.txt` or `requirements-dev.txt`).
- Mock `yfinance.download()` when testing `analyze_ticker()` to avoid network calls and rate limits.
- Snapshot-test the result dict structure from `analyze_ticker()` because the UI relies on exact keys (`_rec_key`, `_market_label`, `Ticker`, `Price`, etc.).
- For UI tests, the desktop app has no automation hooks; focus on `core.py`.

---

## Data Sources & External Dependencies

- **Yahoo Finance** (`yfinance`) — free, rate-limited, occasionally changes API behaviour. The MultiIndex column workaround exists because of past breaking changes.
- **Google Sheets** — requires the sheet to be shared as *"Anyone with the link → Viewer"*. The export URL format is hard-coded and may break if Google changes it.
- **Local files** — CSV or Excel (`.xlsx`, `.xls`). Ticker symbols must be in **column A**, one per row. A header row starting with "ticker" (case-insensitive) is ignored.

---

## Security Considerations

- The app executes **no user-supplied code**; inputs are ticker strings, URLs, and file paths.
- `run_app.bat` uses `powershell -ExecutionPolicy Bypass` to create a shortcut. This is local-only and does not download remote scripts.
- `requests.get()` for Google Sheets has a **10-second timeout** to prevent indefinite hangs.
- No secrets, API keys, or credentials are stored in the repository.

---

## Common Pitfalls for Agents

1. **Do not break the shared `core.py` interface.** Both `app.py` and `desktop_app.py` depend on the exact return keys from `analyze_ticker()`.
2. **`_rec_key`** is the canonical recommendation field for filtering. Do not use the emoji-prefixed `Recommendation` string for programmatic logic.
3. **Thread safety in desktop_app.py:** Never call `window.evaluate_js()` directly from a worker thread. Use `_safe_eval_js()` (or add your own lock-guarded wrapper).
4. **yfinance MultiIndex:** Newer versions return `pd.MultiIndex` columns. The `df.columns = df.columns.get_level_values(0)` line in `analyze_ticker()` is required.
5. **Relative paths:** `desktop_app.py` resolves `ui/index.html` relative to `__file__`. If you move the script, update `get_asset_path()`.
6. **Windows focus:** The batch launcher and shortcut creation are Windows-specific. Cross-platform support would need a replacement for `run_app.bat`.

---

## Quick Reference: Recommendation Logic

| Signal | Condition |
|---|---|
| 🚀 **Strong Buy** | RSI < 30 (Oversold) **AND** MACD Golden Cross |
| ✅ **Buy** | MACD Golden Cross only |
| ⏳ **Wait** | No clear signal |
| ❌ **Sell** | MACD Death Cross only |
| 🔥 **Strong Sell** | RSI > 70 (Overbought) **AND** MACD Death Cross |

---

## Development Focus

> **จากนี้ไปการพัฒนาจะมุ่งเน้นที่ Desktop App (`desktop_app.py` และ `ui/`) เท่านั้น**
>
> ไม่ต้องแก้ไข ปรับปรุง หรือเพิ่มฟีเจอร์ในส่วนของ Streamlit (`app.py`) อีกต่อไป หากมีการเปลี่ยนแปลงใน `core.py` ที่กระทบ `app.py` ให้ทำให้ `app.py` ยังคงทำงานได้ขั้นต่ำ (ไม่พัง) แต่ไม่ต้องเพิ่มฟีเจอร์ใหม่ลงไป

---

*Last updated: 2026-06-04*
