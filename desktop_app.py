import os
import sys
import re
import io
import json
import threading
import webview
import pandas as pd
import requests
import winreg
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

from core import DEFAULT_TICKERS, PRESETS, analyze_ticker

# ── Optional tray icon support ──────────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except Exception:
    _HAS_TRAY = False


def _create_tray_image():
    """Generate a simple 64×64 tray icon (dark bg + green chart line)."""
    width, height = 64, 64
    image = Image.new("RGB", (width, height), (30, 30, 30))
    dc = ImageDraw.Draw(image)
    # Green chart line
    dc.line([(10, 50), (25, 35), (40, 45), (55, 20)], fill=(76, 175, 80), width=4)
    dc.ellipse([(52, 17), (58, 23)], fill=(76, 175, 80))
    return image


def _run_tray_icon(window):
    """Run the system-tray icon in a background thread."""
    if not _HAS_TRAY:
        return

    def on_show(icon, item):
        window.show()

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Show Stock Scanner", on_show),
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon(
        "StockScanner",
        _create_tray_image(),
        "Stock Scanner",
        menu,
    )
    icon.run()


# ─────────────────────────────────────────────────────────────────────────────
# JS-Python Bridge API
# ─────────────────────────────────────────────────────────────────────────────

class PyAPI:
    def __init__(self):
        self.window  = None
        # Serialise evaluate_js calls across threads – pywebview is not thread-safe
        # for concurrent evaluate_js invocations on all backends.
        self._js_lock = threading.Lock()

    def set_window(self, window):
        self.window = window

    # ── Thread-safe JS evaluation ─────────────────────────────────────────────

    def _safe_eval_js(self, js_code: str) -> None:
        """Call window.evaluate_js under a lock so worker threads don't race."""
        if not self.window:
            return
        try:
            with self._js_lock:
                self.window.evaluate_js(js_code)
        except Exception as e:
            print(f"[evaluate_js] {e}")

    # ── Public API (called from JavaScript via pywebview bridge) ──────────────

    def get_default_tickers(self) -> list[str]:
        return DEFAULT_TICKERS

    def select_file(self) -> list[str]:
        """Opens native file dialog for CSV/Excel and parses tickers from column A."""
        if not self.window:
            return []

        file_types = ("Excel Files (*.xlsx;*.xls)", "CSV Files (*.csv)", "All Files (*.*)")
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)

        if not result:
            return []

        filepath = result[0]
        try:
            df = pd.read_csv(filepath, header=None) if filepath.endswith(".csv") \
                 else pd.read_excel(filepath, header=None)
            tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
            return [t for t in tickers if t and not t.lower().startswith("ticker")]
        except Exception as e:
            print(f"[select_file] {e}")
            return []

    def fetch_google_sheet(self, url: str) -> list[str]:
        """Downloads tickers from a public Google Sheet (column A).

        Uses ``requests`` with a 10-second timeout so a bad URL never hangs
        the UI indefinitely.
        """
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            return []

        sheet_id  = m.group(1)
        gid_match = re.search(r"gid=(\d+)", url)
        gid       = gid_match.group(1) if gid_match else "0"
        csv_url   = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/export?format=csv&gid={gid}"
        )

        try:
            response = requests.get(csv_url, timeout=10)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text), header=None)
            tickers = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
            return [t for t in tickers if t and not t.lower().startswith("ticker")]
        except Exception as e:
            print(f"[fetch_google_sheet] {e}")
            return []

    # ── Startup registry helpers ──────────────────────────────────────────────

    def _get_startup_cmd(self) -> str:
        """Build the command string used for Windows startup registry."""
        exe = sys.executable
        # Prefer pythonw.exe so no console window appears on boot
        if exe.lower().endswith("python.exe"):
            pythonw = exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw):
                exe = pythonw
        script = os.path.abspath(__file__)
        return f'"{exe}" "{script}"'

    def set_startup(self, enabled: bool) -> bool:
        """Add or remove this app from Windows startup (HKCU Run)."""
        try:
            app_name = "StockScanner"
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ,
                                      self._get_startup_cmd())
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            print(f"[set_startup] {e}")
            return False

    def get_startup(self) -> bool:
        """Return whether the app is currently set to run on Windows startup."""
        try:
            app_name = "StockScanner"
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, app_name)
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[get_startup] {e}")
            return False

    def save_tickers(self, tickers: list[str]) -> None:
        """Persist ticker list to a local CSV file so it survives app restarts."""
        try:
            path = get_asset_path("last_tickers.csv")
            pd.DataFrame({"Ticker": tickers}).to_csv(path, index=False)
        except Exception as e:
            print(f"[save_tickers] {e}")

    def _fetch_fx_rate(self) -> str:
        """Internal blocking helper for USD/THB."""
        try:
            r = requests.get("https://api.exchangerate-api.com/v4/latest/USD",
                             timeout=10)
            r.raise_for_status()
            return str(r.json()["rates"]["THB"])
        except Exception as e:
            print(f"[_fetch_fx_rate] {e}")
        return ""

    def _fetch_gold_price(self) -> str:
        """Internal blocking helper for gold spot."""
        try:
            df = yf.download("GC=F", period="5d", interval="1h",
                             progress=False, auto_adjust=True)
            if df is not None and len(df) > 0:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                price = float(df["Close"].iloc[-1])
                return str(round(price, 2))
        except Exception as e:
            print(f"[_fetch_gold_price] {e}")
        return ""

    def fetch_market_data(self) -> bool:
        """Kick off a background thread to fetch FX + gold, then push
        results to JS via evaluate_js so the UI never blocks."""
        def _run():
            fx   = self._fetch_fx_rate()
            gold = self._fetch_gold_price()
            payload = json.dumps({"fx": fx, "gold": gold})
            self._safe_eval_js(f"window.onMarketData({payload})")

        threading.Thread(target=_run, daemon=True).start()
        return True

    def load_last_tickers(self) -> list[str]:
        """Load the last persisted ticker list from CSV."""
        try:
            path = get_asset_path("last_tickers.csv")
            if not os.path.exists(path):
                return []
            df = pd.read_csv(path)
            return df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        except Exception as e:
            print(f"[load_last_tickers] {e}")
            return []

    def scan_tickers(self, tickers: list[str], preset_name: str) -> list[dict]:
        """Scan tickers in parallel and push live progress to the UI.

        Worker threads call ``_safe_eval_js`` (which holds a lock) so that
        concurrent ``evaluate_js`` calls are serialised and thread-safe.
        """
        if preset_name not in PRESETS:
            preset_name = "Day"

        p     = PRESETS[preset_name]
        total = len(tickers)

        # Cap workers to the actual number of tickers to avoid idle threads
        max_workers = min(8, total)

        def run_task(index_ticker: tuple[int, str]) -> dict | None:
            idx, ticker = index_ticker
            res = analyze_ticker(
                ticker,
                rsi_period   = p["rsi"],
                macd_fast    = p["fast"],
                macd_slow    = p["slow"],
                macd_signal  = p["signal"],
                interval     = p["interval"],
                dl_period    = p["dl_period"],
                timeframe_label = p["label"],
            )
            # Push incremental progress to JS (thread-safe via lock)
            safe_res = json.dumps(res) if res else "null"
            self._safe_eval_js(
                f"window.onTickerScanned({idx + 1}, {total}, {safe_res})"
            )
            return res

        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for res in executor.map(run_task, enumerate(tickers)):
                if res:
                    results.append(res)

        return results


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_asset_path(filename: str) -> str:
    """Resolve path relative to the script/bundle directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, filename)


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    api      = PyAPI()
    html_path = get_asset_path("ui/index.html")

    if not os.path.exists(html_path):
        print(f"Error: UI files not found at {html_path}")
        sys.exit(1)

    window = webview.create_window(
        "Stock Scanner 📈",
        html_path,
        js_api           = api,
        width            = 1120,
        height           = 820,
        min_size         = (900, 600),
        background_color = "#1E1E1E",
    )
    api.set_window(window)

    # Intercept close (X) button → hide to tray instead of quitting
    def on_window_closing():
        window.hide()
        return False

    window.events.closing += on_window_closing

    # Launch system-tray icon on a background thread
    if _HAS_TRAY:
        tray_thread = threading.Thread(
            target=_run_tray_icon, args=(window,), daemon=True
        )
        tray_thread.start()

    webview.start(debug=False)
