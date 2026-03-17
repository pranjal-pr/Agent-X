const form = document.getElementById("analyze-form");
const tickerInput = document.getElementById("ticker");
const submitButton = document.getElementById("submit-button");
const themeToggle = document.getElementById("theme-toggle");
const themeToggleText = document.getElementById("theme-toggle-text");
const backgroundPresetButtons = Array.from(document.querySelectorAll("[data-background-preset]"));
const resultsSection = document.getElementById("results");
const statusBadge = document.getElementById("status-badge");
const latencyPill = document.getElementById("latency-pill");
const metricTemplate = document.getElementById("metric-card-template");

const stanceEl = document.getElementById("stance");
const confidenceRing = document.getElementById("confidence-ring");
const confidenceValueEl = document.getElementById("confidence-value");
const timeHorizonEl = document.getElementById("time-horizon");
const thesisEl = document.getElementById("thesis");
const modelPill = document.getElementById("model-pill");
const trendPill = document.getElementById("trend-pill");
const metricsGrid = document.getElementById("metrics-grid");
const technicalSummaryEl = document.getElementById("technical-summary");
const catalystsList = document.getElementById("catalysts-list");
const risksList = document.getElementById("risks-list");
const newsSummaryEl = document.getElementById("news-summary");
const newsList = document.getElementById("news-list");
const actionPlanEl = document.getElementById("action-plan");
const THEME_STORAGE_KEY = "stock-syndicate-theme";
const BACKGROUND_STORAGE_KEY = "stock-syndicate-background";
const DEFAULT_BACKGROUND_PRESET = "aurora";

function getPreferredTheme() {
  try {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
      return storedTheme;
    }
  } catch {
    // Ignore storage access failures and fall back to the system preference.
  }

  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function syncThemeToggle() {
  const isDark = document.documentElement.dataset.theme === "dark";
  themeToggle.setAttribute("aria-pressed", String(isDark));
  themeToggleText.textContent = isDark ? "Light mode" : "Dark mode";
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage access failures and keep the theme for this session only.
  }
  syncThemeToggle();
}

setTheme(document.documentElement.dataset.theme || getPreferredTheme());

themeToggle.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  setTheme(nextTheme);
});

function syncBackgroundPresetButtons() {
  const activePreset = document.documentElement.dataset.background || DEFAULT_BACKGROUND_PRESET;
  backgroundPresetButtons.forEach((button) => {
    const isActive = button.dataset.backgroundPreset === activePreset;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function setBackgroundPreset(preset) {
  document.documentElement.dataset.background = preset;
  try {
    localStorage.setItem(BACKGROUND_STORAGE_KEY, preset);
  } catch {
    // Ignore storage access failures and keep the preset for this session only.
  }
  syncBackgroundPresetButtons();
}

setBackgroundPreset(document.documentElement.dataset.background || DEFAULT_BACKGROUND_PRESET);

backgroundPresetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setBackgroundPreset(button.dataset.backgroundPreset || DEFAULT_BACKGROUND_PRESET);
  });
});

function setStatus(label, kind) {
  statusBadge.textContent = label;
  statusBadge.className = `status-badge ${kind}`;
}

function formatPrice(value, currency = "USD") {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `$${Number(value).toFixed(2)}`;
  }
}

function formatPercent(value) {
  return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
}

function createMetric(label, value) {
  const fragment = metricTemplate.content.cloneNode(true);
  fragment.querySelector(".metric-label").textContent = label;
  fragment.querySelector(".metric-value").textContent = value;
  return fragment;
}

function renderList(target, items) {
  target.replaceChildren();
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderMetrics(technicals) {
  metricsGrid.replaceChildren();
  const currency = technicals.currency || "USD";
  const metrics = [
    ["Price", formatPrice(technicals.price, currency)],
    ["Move", formatPercent(technicals.change_percent || 0)],
    ["RSI (14)", technicals.rsi_14.toFixed(2)],
    ["SMA 20", technicals.sma_20.toFixed(2)],
    ["SMA 50", technicals.sma_50.toFixed(2)],
    ["Volume", new Intl.NumberFormat("en-US").format(technicals.volume)],
  ];

  metrics.forEach(([label, value]) => {
    metricsGrid.appendChild(createMetric(label, value));
  });
}

function renderNewsItems(items) {
  newsList.replaceChildren();
  items.forEach((item) => {
    const article = document.createElement("article");
    article.className = "news-item";

    const header = document.createElement("div");
    header.className = "news-item-header";

    const title = document.createElement("h3");
    title.textContent = item.title;

    const meta = document.createElement("span");
    meta.className = "news-meta";
    meta.textContent = item.source || "Unknown source";

    const summary = document.createElement("p");
    summary.textContent = item.summary;

    const link = document.createElement("a");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Open source";

    header.append(title, meta);
    article.append(header, summary, link);
    newsList.appendChild(article);
  });
}

function renderResult(payload) {
  resultsSection.classList.remove("hidden");
  stanceEl.textContent = payload.recommendation.stance;
  confidenceValueEl.textContent = `${Math.round(payload.recommendation.confidence * 100)}%`;
  confidenceRing.style.setProperty("--ring-fill", String(payload.recommendation.confidence * 100));
  timeHorizonEl.textContent = `Time horizon: ${payload.recommendation.time_horizon}`;
  thesisEl.textContent = payload.recommendation.thesis;
  modelPill.textContent = (payload.model || "").trim();
  trendPill.textContent = `Trend: ${payload.technicals.trend_signal}`;
  technicalSummaryEl.textContent = payload.recommendation.technical_summary;
  newsSummaryEl.textContent = payload.recommendation.news_summary;
  actionPlanEl.textContent = payload.recommendation.action_plan;
  latencyPill.textContent = `${payload.latency_seconds.toFixed(2)}s end-to-end`;

  renderMetrics(payload.technicals);
  renderList(catalystsList, payload.recommendation.catalysts);
  renderList(risksList, payload.recommendation.risks);
  renderNewsItems(payload.news.items || []);
}

async function analyzeTicker(ticker) {
  setStatus("Running agents", "running");
  latencyPill.textContent = "Groq inference in progress";
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ticker }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Analysis request failed.");
    }

    renderResult(payload);
    setStatus("Report ready", "done");
  } catch (error) {
    setStatus("Analysis failed", "error");
    latencyPill.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const ticker = tickerInput.value.trim().toUpperCase();
  if (!ticker) {
    setStatus("Ticker required", "error");
    latencyPill.textContent = "Enter a stock symbol such as NVDA.";
    return;
  }

  analyzeTicker(ticker);
});

document.querySelectorAll("[data-ticker]").forEach((button) => {
  button.addEventListener("click", () => {
    const ticker = button.dataset.ticker;
    tickerInput.value = ticker;
    analyzeTicker(ticker);
  });
});
