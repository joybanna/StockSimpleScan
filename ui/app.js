// ── Preset Metadata ──
const PRESETS = {
    "Day":   { label: "Daily",   period: "6 months", rsi: 14, macd: "12/26/9" },
    "Week":  { label: "Weekly",  period: "2 years",  rsi: 14, macd: "12/26/9" },
    "Month": { label: "Monthly", period: "5 years",  rsi: 14, macd: "12/26/9" }
};

// ── App State ──
let appState = {
    tickers:   [],
    timeframe: "Day",
    source:    "manual",
    theme:     "dark",
    results:   []
};

// ── Auto-refresh State ──
let refreshState = {
    intervalId: null,
    intervalMinutes: 0,
    lastRefresh: null,
    nextRefresh: null,
    isScanning: false
};

// ── DOM Elements ──
const elements = {
    btnThemeToggle:  document.getElementById("btn-theme-toggle"),
    btnHelp:         document.getElementById("btn-help"),
    btnCloseHelp:    document.getElementById("btn-close-help"),
    helpModal:       document.getElementById("help-modal"),

    sourceTabs:      document.getElementById("source-tabs"),
    timeframePresets: document.getElementById("timeframe-presets"),
    presetDetails:   document.getElementById("preset-details"),

    // Inputs
    txtTickers:      document.getElementById("txt-tickers"),
    txtSheetUrl:     document.getElementById("txt-sheet-url"),
    btnLoadSheet:    document.getElementById("btn-load-sheet"),
    btnSelectFile:   document.getElementById("btn-select-file"),
    lblFileStatus:   document.getElementById("lbl-file-status"),
    lblTickerCount:  document.getElementById("lbl-ticker-count"),

    // Scan trigger
    btnScan:         document.getElementById("btn-scan"),
    chkStartup:      document.getElementById("chk-startup"),

    // States
    stateWelcome:    document.getElementById("state-welcome"),
    stateScanning:   document.getElementById("state-scanning"),
    stateResults:    document.getElementById("state-results"),
    btnLoadDefault:  document.getElementById("btn-load-default"),

    // Scan indicators
    lblScanStatus:   document.getElementById("lbl-scan-status"),
    lblScanTicker:   document.getElementById("lbl-scan-ticker"),
    barScanProgress: document.getElementById("bar-scan-progress"),
    lblScanPct:      document.getElementById("lbl-scan-pct"),

    // Summary metric cards
    valStrongBuy:    document.getElementById("val-strong-buy"),
    lstStrongBuy:    document.getElementById("lst-strong-buy"),
    valBuy:          document.getElementById("val-buy"),
    lstBuy:          document.getElementById("lst-buy"),
    valSell:         document.getElementById("val-sell"),
    lstSell:         document.getElementById("lst-sell"),
    valStrongSell:   document.getElementById("val-strong-sell"),
    lstStrongSell:   document.getElementById("lst-strong-sell"),

    resultsTables:   document.getElementById("results-tables"),

    // Refresh controls
    selRefresh:      document.getElementById("sel-refresh"),
    btnRefreshNow:   document.getElementById("btn-refresh-now"),
    lblLastRefresh:  document.getElementById("lbl-last-refresh"),
    lblNextRefresh:  document.getElementById("lbl-next-refresh"),

    // Market overview cards
    valFx:           document.getElementById("val-fx"),
    valGold:         document.getElementById("val-gold")
};

// ── Initialization & Storage ──
document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    updateThemeUI();
    updatePresetDetails();
    setupEventListeners();

    // Wait for pywebview API to be ready before loading persisted tickers
    window.addEventListener("pywebviewready", () => {
        // Load startup preference
        window.pywebview.api.get_startup()
            .then(enabled => {
                if (elements.chkStartup) elements.chkStartup.checked = enabled;
            })
            .catch(() => {});

        // Restore auto-refresh interval (without immediate scan on boot)
        const savedInterval = localStorage.getItem("refreshInterval");
        if (savedInterval && elements.selRefresh) {
            elements.selRefresh.value = savedInterval;
            startAutoRefresh(parseInt(savedInterval), false);
        }

        // Start 1-second countdown updater for the refresh timer display
        setInterval(updateRefreshDisplay, 1000);

        // Fetch FX + gold on a background thread (non-blocking)
        window.pywebview.api.fetch_market_data();

        window.pywebview.api.load_last_tickers()
            .then(tickers => {
                if (tickers && tickers.length > 0) {
                    elements.txtTickers.value = tickers.join(", ");
                    appState.tickers = tickers;
                    updateTickerCountBadge();
                } else {
                    const savedTickers = localStorage.getItem("tickers");
                    if (savedTickers) elements.txtTickers.value = savedTickers;
                    parseTickersFromUI();
                }
            })
            .catch(() => {
                const savedTickers = localStorage.getItem("tickers");
                if (savedTickers) elements.txtTickers.value = savedTickers;
                parseTickersFromUI();
            });
    });
});

function loadSettings() {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) appState.theme = savedTheme;
    document.documentElement.setAttribute("data-theme", appState.theme);

    const savedInterval = localStorage.getItem("refreshInterval");
    if (savedInterval && elements.selRefresh) {
        elements.selRefresh.value = savedInterval;
    }

    // Ticker loading is deferred to pywebviewready so Python can supply
    // the persisted CSV file (which takes priority over localStorage).
}

function saveSettings() {
    localStorage.setItem("theme",   appState.theme);
    localStorage.setItem("tickers", elements.txtTickers.value);

    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.save_tickers(appState.tickers).catch(() => {});
    }
}

// ── Event Listeners ──
function setupEventListeners() {

    // Theme toggle
    elements.btnThemeToggle.addEventListener("click", () => {
        appState.theme = appState.theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", appState.theme);
        saveSettings();
        updateThemeUI();
    });

    // Startup toggle
    if (elements.chkStartup) {
        elements.chkStartup.addEventListener("change", () => {
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.set_startup(elements.chkStartup.checked)
                    .then(ok => {
                        if (!ok) {
                            elements.chkStartup.checked = !elements.chkStartup.checked;
                            alert("Unable to change startup setting.");
                        }
                    })
                    .catch(() => {
                        elements.chkStartup.checked = !elements.chkStartup.checked;
                        alert("Unable to change startup setting.");
                    });
            }
        });
    }

    // Help dialog
    elements.btnHelp.addEventListener("click", () => elements.helpModal.classList.add("active"));
    elements.btnCloseHelp.addEventListener("click", () => elements.helpModal.classList.remove("active"));
    elements.helpModal.addEventListener("click", (e) => {
        if (e.target === elements.helpModal) elements.helpModal.classList.remove("active");
    });

    // Source tab switching
    elements.sourceTabs.querySelectorAll("button").forEach(tab => {
        tab.addEventListener("click", (e) => {
            elements.sourceTabs.querySelector(".active").classList.remove("active");
            e.target.classList.add("active");
            appState.source = e.target.dataset.source;

            document.querySelectorAll(".input-panel .input-section").forEach(sec => {
                sec.classList.remove("active");
            });
            document.getElementById(`sec-${appState.source}`).classList.add("active");
            parseTickersFromUI();
        });
    });

    // Timeframe presets
    elements.timeframePresets.querySelectorAll("button").forEach(tab => {
        tab.addEventListener("click", (e) => {
            elements.timeframePresets.querySelector(".active").classList.remove("active");
            e.target.classList.add("active");
            appState.timeframe = e.target.dataset.preset;
            updatePresetDetails();
        });
    });

    // Manual input live update
    elements.txtTickers.addEventListener("input", () => {
        parseTickersFromUI();
        saveSettings();
    });

    // Default tickers shortcut
    elements.btnLoadDefault.addEventListener("click", () => {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_default_tickers().then(defaults => {
                elements.txtTickers.value = defaults.join(", ");
                document.getElementById("btn-src-manual").click();
                parseTickersFromUI();
                saveSettings();
            });
        }
    });

    // Google Sheets loader — errors are shown inline instead of alert()
    elements.btnLoadSheet.addEventListener("click", () => {
        const url = elements.txtSheetUrl.value.trim();
        if (!url) return;

        elements.btnLoadSheet.disabled    = true;
        elements.btnLoadSheet.textContent = "Loading...";

        window.pywebview.api.fetch_google_sheet(url)
            .then(tickers => {
                elements.btnLoadSheet.disabled    = false;
                elements.btnLoadSheet.textContent = "Fetch Sheet";

                if (tickers && tickers.length > 0) {
                    appState.tickers = tickers;
                    updateTickerCountBadge();
                } else {
                    showSheetError("Failed to load — verify sheet is public and URL is correct.");
                }
            })
            .catch(() => {
                elements.btnLoadSheet.disabled    = false;
                elements.btnLoadSheet.textContent = "Fetch Sheet";
                showSheetError("Network error or request timed out (10 s).");
            });
    });

    // Native file selection
    elements.btnSelectFile.addEventListener("click", () => {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.select_file().then(tickers => {
                if (tickers && tickers.length > 0) {
                    appState.tickers = tickers;
                    elements.lblFileStatus.textContent = `${tickers.length} tickers loaded`;
                } else {
                    elements.lblFileStatus.textContent = "No tickers found / dialog cancelled";
                    appState.tickers = [];
                }
                updateTickerCountBadge();
            });
        }
    });

    // Run scan
    elements.btnScan.addEventListener("click", runScan);

    // Auto-refresh interval selector
    if (elements.selRefresh) {
        elements.selRefresh.addEventListener("change", (e) => {
            const minutes = parseInt(e.target.value);
            startAutoRefresh(minutes, true);
        });
    }

    // Manual refresh now
    if (elements.btnRefreshNow) {
        elements.btnRefreshNow.addEventListener("click", () => {
            if (refreshState.isScanning) return;
            runScan();
            // Reset the auto-refresh timer if active
            if (refreshState.intervalMinutes > 0) {
                refreshState.nextRefresh = Date.now() + refreshState.intervalMinutes * 60 * 1000;
                updateRefreshDisplay();
            }
        });
    }
}

// ── UI Helpers ──
function updateThemeUI() {
    // Icon display is controlled purely by CSS [data-theme] selectors
}

function updatePresetDetails() {
    const meta = PRESETS[appState.timeframe];
    elements.presetDetails.innerHTML = `
        Candle: &nbsp;<b>${meta.label}</b> &nbsp;·&nbsp; Lookback: <b>${meta.period}</b><br>
        RSI period: <b>${meta.rsi}</b> &nbsp;·&nbsp; MACD: <b>${meta.macd}</b><br>
        Fibonacci: swing high/low 50 candles · levels 0–161.8%
    `;
}

function parseTickersFromUI() {
    if (appState.source === "manual") {
        const raw = elements.txtTickers.value;
        appState.tickers = raw.split(",")
            .map(t => t.trim().toUpperCase())
            .filter(t => t.length > 0);
    }
    updateTickerCountBadge();
}

function updateTickerCountBadge() {
    const count = appState.tickers.length;
    elements.lblTickerCount.textContent = `${count} ${count === 1 ? "ticker" : "tickers"} loaded`;
    elements.btnScan.disabled = count === 0;
}

function showSheetError(msg) {
    const hint = document.querySelector("#sec-sheet .hint-text");
    const orig = "Sheet must be public (\"Anyone with link can view\"). Put tickers in Column A.";
    if (hint) {
        hint.style.color = "var(--danger)";
        hint.textContent = msg;
        setTimeout(() => {
            hint.style.color = "";
            hint.textContent = orig;
        }, 5000);
    }
}

// ── Auto-refresh helpers ──
function startAutoRefresh(minutes, scanImmediately = false) {
    stopAutoRefresh();
    if (minutes <= 0) {
        localStorage.removeItem("refreshInterval");
        updateRefreshDisplay();
        return;
    }

    refreshState.intervalMinutes = parseInt(minutes);
    localStorage.setItem("refreshInterval", minutes);

    if (scanImmediately && !refreshState.isScanning) {
        runScan();
    } else {
        refreshState.nextRefresh = Date.now() + minutes * 60 * 1000;
        updateRefreshDisplay();
    }

    refreshState.intervalId = setInterval(() => {
        if (!refreshState.isScanning) {
            runScan();
        }
    }, minutes * 60 * 1000);
}

function stopAutoRefresh() {
    if (refreshState.intervalId) {
        clearInterval(refreshState.intervalId);
        refreshState.intervalId = null;
    }
    refreshState.intervalMinutes = 0;
    refreshState.nextRefresh = null;
}

function updateRefreshDisplay() {
    const lastEl = elements.lblLastRefresh;
    const nextEl = elements.lblNextRefresh;
    if (!lastEl || !nextEl) return;

    if (refreshState.lastRefresh) {
        lastEl.textContent = "Last: " + formatTime(refreshState.lastRefresh);
    } else {
        lastEl.textContent = "Last: —";
    }

    if (refreshState.nextRefresh && refreshState.intervalMinutes > 0) {
        const remaining = Math.max(0, Math.ceil((refreshState.nextRefresh - Date.now()) / 1000));
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        nextEl.textContent = `Next: ${mins}m ${secs}s`;
    } else {
        nextEl.textContent = "Next: —";
    }
}

// ── Callback called from Python background thread ──
window.onMarketData = function(payload) {
    console.log("[onMarketData]", payload);
    if (payload.fx && payload.fx !== "") {
        elements.valFx.textContent = payload.fx;
    } else {
        elements.valFx.textContent = "—";
    }
    if (payload.gold && payload.gold !== "") {
        elements.valGold.textContent = "$" + payload.gold;
    } else {
        elements.valGold.textContent = "—";
    }
};

function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ── Scan Execution ──
function runScan() {
    if (appState.tickers.length === 0 || refreshState.isScanning) return;

    refreshState.isScanning = true;
    appState.results = [];
    switchState("scanning");
    updateProgressBar(0, appState.tickers.length, "");

    window.pywebview.api.scan_tickers(appState.tickers, appState.timeframe)
        .then(finalResults => {
            appState.results = finalResults;
            renderResults();
            switchState("results");

            refreshState.lastRefresh = new Date();
            if (refreshState.intervalMinutes > 0) {
                refreshState.nextRefresh = Date.now() + refreshState.intervalMinutes * 60 * 1000;
            }
            refreshState.isScanning = false;
            updateRefreshDisplay();
            window.pywebview.api.fetch_market_data();
        })
        .catch(err => {
            console.error("Scan error:", err);
            switchState("welcome");
            alert("An error occurred during scanning: " + err);
            refreshState.isScanning = false;
            updateRefreshDisplay();
            window.pywebview.api.fetch_market_data();
        });
}

// Called from Python backend via window.evaluate_js (one call per ticker)
window.onTickerScanned = function(current, total, result) {
    const pct    = Math.round((current / total) * 100);
    const ticker = result ? result.Ticker : "...";
    updateProgressBar(pct, total, `Processing ${ticker} (${current}/${total})`);
};

function updateProgressBar(pct, total, text) {
    elements.barScanProgress.style.width = `${pct}%`;
    elements.lblScanPct.textContent      = `${pct}%`;
    if (text) elements.lblScanTicker.textContent = text;
}

function switchState(state) {
    elements.stateWelcome.classList.remove("active");
    elements.stateScanning.classList.remove("active");
    elements.stateResults.classList.remove("active");

    if (state === "welcome")  elements.stateWelcome.classList.add("active");
    if (state === "scanning") elements.stateScanning.classList.add("active");
    if (state === "results")  elements.stateResults.classList.add("active");
}

// ── Results Rendering ──
function renderResults() {
    // 1. Summary cards — use _rec_key (raw signal string, no emoji) for
    //    reliable filtering; avoids false positives from error messages.
    const strongBuys  = appState.results.filter(r => r._rec_key === "STRONG BUY").map(r => r.Ticker);
    const buys        = appState.results.filter(r => r._rec_key === "BUY").map(r => r.Ticker);
    const sells       = appState.results.filter(r => r._rec_key === "SELL").map(r => r.Ticker);
    const strongSells = appState.results.filter(r => r._rec_key === "STRONG SELL").map(r => r.Ticker);

    elements.valStrongBuy.textContent  = strongBuys.length;
    elements.lstStrongBuy.textContent  = strongBuys.length  > 0 ? strongBuys.join(", ")  : "-";

    elements.valBuy.textContent        = buys.length;
    elements.lstBuy.textContent        = buys.length        > 0 ? buys.join(", ")        : "-";

    elements.valSell.textContent       = sells.length;
    elements.lstSell.textContent       = sells.length       > 0 ? sells.join(", ")       : "-";

    elements.valStrongSell.textContent = strongSells.length;
    elements.lstStrongSell.textContent = strongSells.length > 0 ? strongSells.join(", ") : "-";

    // 2. Group by market label
    const groups = {};
    appState.results.forEach(row => {
        const label = row._market_label;
        if (!groups[label]) groups[label] = [];
        groups[label].push(row);
    });

    // Sort: US first, Thailand second, rest alphabetically
    const sortedMarketLabels = Object.keys(groups).sort((a, b) => {
        const aUS = a.includes("US");
        const bUS = b.includes("US");
        const aTH = a.includes("Thailand");
        const bTH = b.includes("Thailand");
        if (aUS && !bUS) return -1;
        if (!aUS && bUS) return  1;
        if (aTH && !bTH) return -1;
        if (!aTH && bTH) return  1;
        return a.localeCompare(b);
    });

    // 3. Render grouped tables
    elements.resultsTables.innerHTML = "";

    if (appState.results.length === 0) {
        elements.resultsTables.innerHTML = `
            <div class="welcome-card" style="box-shadow:none;border:none;background:transparent;">
                <p>No valid data returned. Check symbols and network connection.</p>
            </div>`;
        return;
    }

    sortedMarketLabels.forEach(label => {
        elements.resultsTables.appendChild(
            generateMarketTableHTML(label, groups[label])
        );
    });
}

function generateMarketTableHTML(marketLabel, rows) {
    const section = document.createElement("section");
    section.className = "market-group";

    section.innerHTML = `
        <div class="market-header">
            <h2>${marketLabel}</h2>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Price Date</th>
                        <th>RSI (${PRESETS[appState.timeframe].rsi})</th>
                        <th>RSI Status</th>
                        <th>MACD Status</th>
                        <th>Recommendation</th>
                        <th>Fib Resist</th>
                        <th>Fib Support</th>
                        <th>Upside</th>
                        <th>Downside</th>
                        <th>R/R</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(r => {
                        const rsiClass = getBadgeClass(r._rec_key, r.RSI_Status);
                        const macdClass = getBadgeClass(r._rec_key, r.MACD_Status);
                        const recClass  = getRecBadgeClass(r._rec_key);
                        const rrVal  = parseFloat(r.RR);
                        const rrClass = rrVal >= 1.0 ? "text-green" : "";
                        return `
                            <tr>
                                <td><strong>${r.Ticker}</strong></td>
                                <td>${r.Price}</td>
                                <td><span style="font-size:0.75rem;color:var(--text-muted);">${r.PriceDate}</span></td>
                                <td>${r.RSI}</td>
                                <td><span class="badge ${rsiClass}">${r.RSI_Status}</span></td>
                                <td><span class="badge ${macdClass}">${r.MACD_Status}</span></td>
                                <td><span class="badge ${recClass}">${r.Recommendation}</span></td>
                                <td>${r.Fib_Resist}</td>
                                <td>${r.Fib_Support}</td>
                                <td class="text-green">${r.Upside}</td>
                                <td class="text-red">${r.Downside}</td>
                                <td class="${rrClass}">${r.RR}</td>
                            </tr>`;
                    }).join("")}
                </tbody>
            </table>
        </div>`;
    return section;
}

/**
 * Badge colour for RSI / MACD status columns.
 * Uses the plain status string (not recommendation) for colouring.
 */
function getBadgeClass(recKey, statusText) {
    if (!statusText || statusText === "-") return "muted";
    const s = statusText.toUpperCase();
    if (s.includes("OVERSOLD")     || s.includes("GOLDEN CROSS")) return "success";
    if (s.includes("OVERBOUGHT")   || s.includes("DEATH CROSS"))  return "danger";
    if (s.includes("NEUTRAL")      || s.includes("STEADY"))       return "muted";
    return "muted";
}

/**
 * Badge colour for the Recommendation column.
 * Uses the raw _rec_key for exact, emoji-safe matching.
 */
function getRecBadgeClass(recKey) {
    if (!recKey || recKey === "ERROR") return "muted";
    switch (recKey) {
        case "STRONG BUY":  return "success";
        case "BUY":         return "info";
        case "WAIT":        return "muted";
        case "SELL":        return "warning";
        case "STRONG SELL": return "danger";
        default:            return "muted";
    }
}
