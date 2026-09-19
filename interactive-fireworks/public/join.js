import { createClientId } from "./client-id.js";

const params = new URLSearchParams(location.search);
const room = (params.get("room") || "lobby").toLowerCase();
const protocol = location.protocol === "https:" ? "wss:" : "ws:";
const wsUrl = `${protocol}//${location.host}/ws`;
const clientIdKey = "interactive-fireworks-client-id";
const clientId = localStorage.getItem(clientIdKey) || createClientId();
localStorage.setItem(clientIdKey, clientId);

const wishText = document.querySelector("#wishText");
const wishName = document.querySelector("#wishName");
const textCount = document.querySelector("#textCount");
const launcher = document.querySelector("#launcher");
const statusDot = document.querySelector("#statusDot");
const connectionLabel = document.querySelector("#connectionLabel");
const successOverlay = document.querySelector("#successOverlay");
const successTitle = document.querySelector("#successTitle");
const successMessage = document.querySelector("#successMessage");
const toast = document.querySelector("#toast");
const brandName = document.querySelector("#brandName");
const mobileTitle = document.querySelector("#mobileTitle");
const mobileSubtitle = document.querySelector("#mobileSubtitle");
const templates = document.querySelector("#templates");
const launcherTitle = document.querySelector("#launcherTitle");
const launcherTip = document.querySelector("#launcherTip");
const shapeOptions = document.querySelectorAll(".shape-option");
const styleOptions = document.querySelectorAll(".style-option");

let socket;
let reconnectTimer;
let selectedColor = "gold";
let selectedShape = "burst";
let selectedStyle = "velvet";
let startY = null;
let pendingRequestId = null;
let toastTimer;
let currentConfig = {
  brand: "星河心愿",
  mobileTitle: "写下此刻的祝福",
  mobileSubtitle: "向上滑动，让心愿在现场大屏绽放",
  templates: ["万事顺遂，平安喜乐", "所愿皆所得，所行皆坦途", "新岁启封，好运常在"],
  submissionsEnabled: true,
  maxWishLength: 28,
  maxNameLength: 8,
};

function updateTextCount() {
  textCount.textContent = `${wishText.value.length}/${currentConfig.maxWishLength}`;
}

function applyConfig(config) {
  if (!config) return;
  currentConfig = { ...currentConfig, ...config };
  brandName.textContent = currentConfig.brand;
  mobileTitle.textContent = currentConfig.mobileTitle;
  mobileSubtitle.textContent = currentConfig.mobileSubtitle;
  wishText.maxLength = currentConfig.maxWishLength;
  wishName.maxLength = currentConfig.maxNameLength;
  templates.replaceChildren();
  for (const template of currentConfig.templates) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = template;
    templates.appendChild(button);
  }
  launcher.classList.toggle("disabled", !currentConfig.submissionsEnabled);
  launcher.setAttribute("aria-disabled", String(!currentConfig.submissionsEnabled));
  launcherTitle.textContent = currentConfig.submissionsEnabled ? "向上滑动发射" : "活动暂未开放";
  launcherTip.textContent = currentConfig.submissionsEnabled ? "也可以轻触这里" : "请稍后再试";
  document.title = `${currentConfig.brand} · 发射祝福烟花`;
  updateTextCount();
}

wishText.addEventListener("input", updateTextCount);
templates.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  wishText.value = button.textContent.trim().slice(0, currentConfig.maxWishLength);
  wishText.dispatchEvent(new Event("input"));
  wishText.focus();
});
document.querySelectorAll(".color-dot").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".color-dot").forEach((item) => item.classList.remove("selected"));
    button.classList.add("selected");
    selectedColor = button.dataset.color;
  });
});
shapeOptions.forEach((button) => {
  button.addEventListener("click", () => {
    shapeOptions.forEach((item) => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    selectedShape = button.dataset.shape;
  });
});
styleOptions.forEach((button) => {
  button.addEventListener("click", () => {
    styleOptions.forEach((item) => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    selectedStyle = button.dataset.style;
  });
});

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("show");
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

function showSuccess(message, pending = false) {
  successTitle.textContent = pending ? "提交成功" : "发射成功";
  successMessage.textContent = message;
  successOverlay.classList.add("show");
  if (navigator.vibrate) navigator.vibrate([30, 40, 70]);
  setTimeout(() => successOverlay.classList.remove("show"), 2200);
}

function submitWish() {
  if (!currentConfig.submissionsEnabled) {
    showToast("活动暂未开放祝福提交");
    return;
  }
  const text = wishText.value.replace(/\s+/g, " ").trim();
  if (!text) {
    showToast("请先写下一句祝福");
    wishText.focus();
    return;
  }
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    showToast("正在连接大屏，请稍后再试");
    return;
  }
  if (pendingRequestId) return;
  pendingRequestId = createClientId();
  launcher.classList.add("sending");
  socket.send(JSON.stringify({
    type: "submit",
    requestId: pendingRequestId,
    text,
    name: wishName.value.trim(),
    color: selectedColor,
    shape: selectedShape,
    style: selectedStyle,
  }));
  setTimeout(() => {
    if (!pendingRequestId) return;
    pendingRequestId = null;
    launcher.classList.remove("sending");
    showToast("大屏响应较慢，请再试一次");
  }, 7000);
}

launcher.addEventListener("pointerdown", (event) => {
  startY = event.clientY;
  launcher.setPointerCapture?.(event.pointerId);
  launcher.classList.add("dragging");
});
launcher.addEventListener("pointermove", (event) => {
  if (startY === null) return;
  const distance = Math.max(0, startY - event.clientY);
  launcher.style.setProperty("--swipe", `${Math.min(distance, 80)}px`);
  if (distance > 64) {
    startY = null;
    launcher.classList.remove("dragging");
    submitWish();
  }
});
function cancelSwipe() {
  startY = null;
  launcher.classList.remove("dragging");
  launcher.style.removeProperty("--swipe");
}
launcher.addEventListener("pointerup", (event) => {
  if (startY !== null && Math.abs(startY - event.clientY) < 12) submitWish();
  cancelSwipe();
});
launcher.addEventListener("pointercancel", cancelSwipe);
launcher.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    submitWish();
  }
});

function connect() {
  clearTimeout(reconnectTimer);
  socket = new WebSocket(wsUrl);
  socket.addEventListener("open", () => {
    statusDot.classList.add("online");
    connectionLabel.textContent = "已连接现场大屏";
    socket.send(JSON.stringify({ type: "join", room, role: "mobile", clientId }));
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "joined") applyConfig(message.config);
    if (message.type === "config") {
      applyConfig(message.config);
      showToast("活动配置已更新");
    }
    if (message.type === "history-cleared") showToast("祝福墙已清空");
    if (message.type === "accepted" && message.requestId === pendingRequestId) {
      pendingRequestId = null;
      launcher.classList.remove("sending");
      wishText.value = "";
      wishText.dispatchEvent(new Event("input"));
      showSuccess(message.message || "请抬头看大屏");
    }
    if (message.type === "error" && (!message.requestId || message.requestId === pendingRequestId)) {
      pendingRequestId = null;
      launcher.classList.remove("sending");
      showToast(message.message || "发送失败，请重试");
    }
  });
  socket.addEventListener("close", () => {
    statusDot.classList.remove("online");
    connectionLabel.textContent = "正在重新连接";
    reconnectTimer = setTimeout(connect, 1600);
  });
  socket.addEventListener("error", () => socket.close());
}

connect();
