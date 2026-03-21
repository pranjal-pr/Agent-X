const form = document.getElementById("analyze-form");
const tickerInput = document.getElementById("ticker");
const submitButton = document.getElementById("submit-button");
const themeToggle = document.getElementById("theme-toggle");
const themeToggleText = document.getElementById("theme-toggle-text");
const quickPickButtons = Array.from(document.querySelectorAll("[data-ticker]"));
const attachToggle = document.getElementById("attach-toggle");
const attachMenu = document.getElementById("attach-menu");
const attachmentMenuActions = Array.from(document.querySelectorAll("[data-attach-action]"));
const fileUploadInput = document.getElementById("file-upload-input");
const photoUploadInput = document.getElementById("photo-upload-input");
const attachmentList = document.getElementById("attachment-list");
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
const attachmentsPill = document.getElementById("attachments-pill");
const metricsGrid = document.getElementById("metrics-grid");
const technicalSummaryEl = document.getElementById("technical-summary");
const catalystsList = document.getElementById("catalysts-list");
const risksList = document.getElementById("risks-list");
const newsSummaryEl = document.getElementById("news-summary");
const newsList = document.getElementById("news-list");
const actionPlanEl = document.getElementById("action-plan");
const THEME_STORAGE_KEY = "stock-syndicate-theme";
const MAX_ATTACHMENTS = 6;
let selectedAttachments = [];

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

function syncQuickPickSelection() {
  const activeTicker = tickerInput.value.trim().toUpperCase();
  quickPickButtons.forEach((button) => {
    const isActive = button.dataset.ticker === activeTicker;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function formatBytes(sizeBytes) {
  if (sizeBytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function buildAttachmentId(file) {
  return [file.name, file.size, file.lastModified].join(":");
}

function closeAttachMenu() {
  attachMenu.classList.add("hidden");
  attachToggle.setAttribute("aria-expanded", "false");
}

function renderAttachments() {
  attachmentList.replaceChildren();
  attachmentList.classList.toggle("hidden", selectedAttachments.length === 0);

  selectedAttachments.forEach((attachment) => {
    const item = document.createElement("article");
    item.className = "attachment-chip";

    if (attachment.previewUrl) {
      const preview = document.createElement("img");
      preview.className = "attachment-preview";
      preview.alt = `${attachment.file.name} preview`;
      preview.src = attachment.previewUrl;
      item.appendChild(preview);
    } else {
      const badge = document.createElement("span");
      badge.className = "attachment-kind";
      badge.textContent = attachment.kind.toUpperCase();
      item.appendChild(badge);
    }

    const body = document.createElement("div");
    body.className = "attachment-body";

    const name = document.createElement("strong");
    name.textContent = attachment.file.name;

    const meta = document.createElement("span");
    meta.className = "attachment-meta";
    meta.textContent = `${attachment.kind === "photo" ? "Photo" : "File"} - ${formatBytes(attachment.file.size)}`;

    body.append(name, meta);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "attachment-remove";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      if (attachment.previewUrl) {
        URL.revokeObjectURL(attachment.previewUrl);
      }
      selectedAttachments = selectedAttachments.filter((candidate) => candidate.id !== attachment.id);
      renderAttachments();
    });

    item.append(body, removeButton);
    attachmentList.appendChild(item);
  });
}

function mergeAttachments(fileList) {
  const nextAttachments = [...selectedAttachments];

  for (const file of fileList) {
    const id = buildAttachmentId(file);
    if (nextAttachments.some((attachment) => attachment.id === id)) {
      continue;
    }
    if (nextAttachments.length >= MAX_ATTACHMENTS) {
      setStatus("Attachment limit reached", "error");
      latencyPill.textContent = `Attach up to ${MAX_ATTACHMENTS} files or photos per request.`;
      break;
    }

    nextAttachments.push({
      id,
      file,
      kind: file.type.startsWith("image/") ? "photo" : "file",
      previewUrl: file.type.startsWith("image/") ? URL.createObjectURL(file) : null,
    });
  }

  selectedAttachments = nextAttachments;
  renderAttachments();
}

function handleAttachmentSelection(event) {
  const files = Array.from(event.target.files || []);
  if (files.length) {
    mergeAttachments(files);
  }
  event.target.value = "";
}

attachToggle.addEventListener("click", () => {
  const isOpen = !attachMenu.classList.contains("hidden");
  attachMenu.classList.toggle("hidden", isOpen);
  attachToggle.setAttribute("aria-expanded", String(!isOpen));
});

attachmentMenuActions.forEach((button) => {
  button.addEventListener("click", () => {
    closeAttachMenu();
    if (button.dataset.attachAction === "photos") {
      photoUploadInput.click();
      return;
    }
    fileUploadInput.click();
  });
});

[fileUploadInput, photoUploadInput].forEach((input) => {
  input.addEventListener("change", handleAttachmentSelection);
});

document.addEventListener("click", (event) => {
  if (!attachMenu.contains(event.target) && !attachToggle.contains(event.target)) {
    closeAttachMenu();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeAttachMenu();
  }
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
  if ((payload.attachments || []).length) {
    attachmentsPill.textContent = `${payload.attachments.length} attachment${payload.attachments.length === 1 ? "" : "s"}`;
    attachmentsPill.classList.remove("hidden");
  } else {
    attachmentsPill.classList.add("hidden");
  }
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
  latencyPill.textContent =
    selectedAttachments.length > 0
      ? `Uploading ${selectedAttachments.length} attachment${selectedAttachments.length === 1 ? "" : "s"}`
      : "Groq inference in progress";
  submitButton.disabled = true;

  try {
    const requestOptions = { method: "POST" };
    if (selectedAttachments.length > 0) {
      const formData = new FormData();
      formData.append("ticker", ticker);
      selectedAttachments.forEach((attachment) => {
        formData.append("attachments", attachment.file, attachment.file.name);
      });
      requestOptions.body = formData;
    } else {
      requestOptions.headers = {
        "Content-Type": "application/json",
      };
      requestOptions.body = JSON.stringify({ ticker });
    }

    const response = await fetch("/api/analyze", requestOptions);

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

tickerInput.addEventListener("input", () => {
  syncQuickPickSelection();
});

quickPickButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const ticker = button.dataset.ticker;
    tickerInput.value = ticker;
    syncQuickPickSelection();
    tickerInput.focus();
    setStatus("Ticker ready", "idle");
    latencyPill.textContent = `Click Analyze to run ${ticker}.`;
  });
});

syncQuickPickSelection();
