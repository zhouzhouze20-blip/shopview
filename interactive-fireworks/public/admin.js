const params = new URLSearchParams(location.search);
const room = (params.get("room") || "lobby").toLowerCase();
const tokenKey = `interactive-fireworks-admin-token:${room}`;

const loginPanel = document.querySelector("#loginPanel");
const loginForm = document.querySelector("#loginForm");
const tokenInput = document.querySelector("#tokenInput");
const dashboard = document.querySelector("#dashboard");
const logoutButton = document.querySelector("#logoutButton");
const roomLabel = document.querySelector("#roomLabel");
const configForm = document.querySelector("#configForm");
const saveButton = document.querySelector("#saveButton");
const saveState = document.querySelector("#saveState");
const refreshButton = document.querySelector("#refreshButton");
const clearWishesButton = document.querySelector("#clearWishesButton");
const toast = document.querySelector("#toast");

const fields = {
  brand: document.querySelector("#brand"),
  displayKicker: document.querySelector("#displayKicker"),
  displayTitle: document.querySelector("#displayTitle"),
  idleTitle: document.querySelector("#idleTitle"),
  idleSubtitle: document.querySelector("#idleSubtitle"),
  mobileTitle: document.querySelector("#mobileTitle"),
  mobileSubtitle: document.querySelector("#mobileSubtitle"),
  templates: document.querySelector("#templates"),
  submissionsEnabled: document.querySelector("#submissionsEnabled"),
  maxWishLength: document.querySelector("#maxWishLength"),
  maxNameLength: document.querySelector("#maxNameLength"),
  blockedWords: document.querySelector("#blockedWords"),
};

let adminToken = sessionStorage.getItem(tokenKey) || "";
let toastTimer;
let refreshTimer;

roomLabel.textContent = room;

function showToast(message, error = false) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.classList.add("show");
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}

function splitLines(value) {
  return value.split(/\n|,/).map((item) => item.trim()).filter(Boolean);
}

async function adminRequest(path = "", options = {}) {
  const response = await fetch(`/api/admin/rooms/${encodeURIComponent(room)}${path}`, {
    ...options,
    headers: {
      "content-type": "application/json",
      "x-admin-token": adminToken,
      ...options.headers,
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || "后台请求失败");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function fillConfig(config) {
  fields.brand.value = config.brand;
  fields.displayKicker.value = config.displayKicker;
  fields.displayTitle.value = config.displayTitle;
  fields.idleTitle.value = config.idleTitle;
  fields.idleSubtitle.value = config.idleSubtitle;
  fields.mobileTitle.value = config.mobileTitle;
  fields.mobileSubtitle.value = config.mobileSubtitle;
  fields.templates.value = config.templates.join("\n");
  fields.submissionsEnabled.checked = config.submissionsEnabled;
  fields.maxWishLength.value = config.maxWishLength;
  fields.maxNameLength.value = config.maxNameLength;
  fields.blockedWords.value = config.blockedWords.join("\n");
  updateSubmissionStatus(config.submissionsEnabled);
}

function readConfig() {
  return {
    brand: fields.brand.value,
    displayKicker: fields.displayKicker.value,
    displayTitle: fields.displayTitle.value,
    idleTitle: fields.idleTitle.value,
    idleSubtitle: fields.idleSubtitle.value,
    mobileTitle: fields.mobileTitle.value,
    mobileSubtitle: fields.mobileSubtitle.value,
    templates: splitLines(fields.templates.value),
    submissionsEnabled: fields.submissionsEnabled.checked,
    maxWishLength: Number(fields.maxWishLength.value),
    maxNameLength: Number(fields.maxNameLength.value),
    blockedWords: splitLines(fields.blockedWords.value),
  };
}

function updateSubmissionStatus(enabled) {
  document.querySelector("#submissionStatus").textContent = enabled ? "开放" : "暂停";
  document.querySelector("#submissionStatusTip").textContent = enabled ? "祝福立即上屏" : "手机端禁止提交";
  document.querySelector("#submissionStatus").style.color = enabled ? "#6fefbd" : "#ff9eb1";
}

function updateStats(data) {
  document.querySelector("#wishCount").textContent = data.stats.wishCount;
  document.querySelector("#participantCount").textContent = data.stats.participantCount;
  document.querySelector("#displayCount").textContent = data.stats.displayCount;
  document.querySelector("#displayLink").href = data.links.display;
  document.querySelector("#joinLink").href = data.links.join;
  updateSubmissionStatus(data.config.submissionsEnabled);
}

function showDashboard() {
  loginPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  logoutButton.classList.remove("hidden");
}

function showLogin() {
  clearInterval(refreshTimer);
  dashboard.classList.add("hidden");
  logoutButton.classList.add("hidden");
  loginPanel.classList.remove("hidden");
  tokenInput.value = "";
  tokenInput.focus();
}

async function loadDashboard({ quiet = false } = {}) {
  try {
    const data = await adminRequest();
    fillConfig(data.config);
    updateStats(data);
    showDashboard();
    saveState.textContent = "配置已同步";
    if (!quiet) showToast("活动配置已加载");
    clearInterval(refreshTimer);
    refreshTimer = setInterval(() => refreshStats({ quiet: true }), 5000);
  } catch (error) {
    if (error.status === 401 || error.status === 503) {
      sessionStorage.removeItem(tokenKey);
      adminToken = "";
      showLogin();
    }
    if (!quiet) showToast(error.message, true);
  }
}

async function refreshStats({ quiet = false } = {}) {
  try {
    const data = await adminRequest();
    updateStats(data);
    if (!quiet) showToast("活动状态已刷新");
  } catch (error) {
    if (!quiet) showToast(error.message, true);
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  adminToken = tokenInput.value.trim();
  if (!adminToken) return;
  sessionStorage.setItem(tokenKey, adminToken);
  await loadDashboard();
});

logoutButton.addEventListener("click", () => {
  sessionStorage.removeItem(tokenKey);
  adminToken = "";
  showLogin();
});

refreshButton.addEventListener("click", () => refreshStats());
fields.submissionsEnabled.addEventListener("change", () => updateSubmissionStatus(fields.submissionsEnabled.checked));
configForm.addEventListener("input", () => { saveState.textContent = "有未保存的修改"; });

configForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  saveButton.disabled = true;
  saveButton.textContent = "保存中…";
  try {
    const data = await adminRequest("", {
      method: "PUT",
      body: JSON.stringify({ config: readConfig() }),
    });
    fillConfig(data.config);
    saveState.textContent = "刚刚保存并实时生效";
    showToast(data.message || "活动配置已保存");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    saveButton.disabled = false;
    saveButton.textContent = "保存并实时生效";
  }
});

clearWishesButton.addEventListener("click", async () => {
  const confirmed = window.confirm(`确认清空场次“${room}”的全部祝福吗？系统会先自动备份。`);
  if (!confirmed) return;
  clearWishesButton.disabled = true;
  clearWishesButton.textContent = "正在备份并清空…";
  try {
    const data = await adminRequest("/wishes", { method: "DELETE" });
    document.querySelector("#wishCount").textContent = "0";
    showToast(`${data.message}，备份：${data.backupFile}`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    clearWishesButton.disabled = false;
    clearWishesButton.textContent = "清空当前场次祝福";
  }
});

if (adminToken) loadDashboard({ quiet: true });
else showLogin();
