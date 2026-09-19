import { fireworkStyleProfile, heartVelocity, radialVelocity } from "./firework-geometry.js";
import { createWishPlaybackQueue } from "./wish-playback.js";

const params = new URLSearchParams(location.search);
const room = (params.get("room") || "lobby").toLowerCase();
const protocol = location.protocol === "https:" ? "wss:" : "ws:";
const wsUrl = `${protocol}//${location.host}/ws`;

const canvas = document.querySelector("#fireworks");
const ctx = canvas.getContext("2d");
const canvas3d = document.querySelector("#fireworks3d");
const qrCode = document.querySelector("#qrCode");
const roomLabel = document.querySelector("#roomLabel");
const historyList = document.querySelector("#historyList");
const wishCount = document.querySelector("#wishCount");
const participantCount = document.querySelector("#participantCount");
const statusDot = document.querySelector("#statusDot");
const connectionLabel = document.querySelector("#connectionLabel");
const brandName = document.querySelector("#brandName");
const displayKicker = document.querySelector("#displayKicker");
const displayTitle = document.querySelector("#displayTitle");
const idleTitle = document.querySelector("#idleTitle");
const idleSubtitle = document.querySelector("#idleSubtitle");

qrCode.src = `/api/rooms/${encodeURIComponent(room)}/qr.svg`;
roomLabel.textContent = room;

const palettes = {
  gold: ["#fff2a8", "#ffd56a", "#ff9e45"],
  rose: ["#ffe0eb", "#ff769f", "#ff4777"],
  cyan: ["#e2fbff", "#5ce7ff", "#3a9dff"],
  violet: ["#f3e9ff", "#b797ff", "#774dff"],
  emerald: ["#d8fff1", "#63f0bd", "#18b982"],
};

const FRAME_MS = 1000 / 60;
const ASCENT_FRAMES = 42;
const FIREWORK_LIFETIME_FRAMES = 240;
const LAUNCH_INTERVAL_MS = 1050;
const AMBIENT_INTERVAL_MS = 4800;
const WISH_LOOP_INTERVAL_MS = 3600;

let width = 0;
let height = 0;
let dpr = 1;
let socket;
let reconnectTimer;
let history = [];
let totalWishes = 0;
const playbackQueue = createWishPlaybackQueue();
let active = [];
let particles = [];
let lastLaunch = Number.NEGATIVE_INFINITY;
let lastAmbient = 0;
let previousFrame = 0;
let webglRenderer = null;
let rendererMode = "canvas";
const rendererPreference = ["auto", "webgl", "canvas"].includes(params.get("renderer"))
  ? params.get("renderer")
  : "auto";

function activateCanvas(reason = "fallback") {
  webglRenderer?.destroy();
  webglRenderer = null;
  rendererMode = "canvas";
  canvas.hidden = false;
  canvas3d.hidden = true;
  document.body.dataset.renderer = "canvas";
  document.body.dataset.rendererReason = reason;
}

async function initializeRenderer() {
  if (rendererPreference === "canvas") {
    activateCanvas("forced");
    return;
  }
  try {
    const { createWebGLFireworksRenderer } = await import("./fireworks-webgl.js");
    webglRenderer = createWebGLFireworksRenderer({
      canvas: canvas3d,
      onFallback: (reason) => activateCanvas(reason),
      onLabel: showWishLabel,
      onQuality: (tier) => { document.body.dataset.quality = tier; },
      onMetrics: ({ fps }) => { document.body.dataset.fps = String(fps); },
    });
    rendererMode = "webgl";
    canvas.hidden = true;
    canvas3d.hidden = false;
    document.body.dataset.renderer = "webgl";
    document.body.dataset.rendererReason = rendererPreference;
  } catch (error) {
    console.warn("WebGL fireworks unavailable, using Canvas fallback", error);
    activateCanvas("initialization-failed");
  }
}

function launchWish(wish, ambient = false) {
  if (rendererMode === "webgl" && webglRenderer) {
    webglRenderer.launch(wish, { ambient });
    return;
  }
  active.push(new Firework(wish, ambient));
}

function applyConfig(config) {
  if (!config) return;
  brandName.textContent = config.brand;
  displayKicker.textContent = config.displayKicker;
  displayTitle.textContent = config.displayTitle;
  idleTitle.textContent = config.idleTitle;
  idleSubtitle.textContent = config.idleSubtitle;
  document.title = `${config.brand} · 烟花互动大屏`;
}

function resize() {
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener("resize", resize);
resize();

class Firework {
  constructor(wish, ambient = false) {
    this.wish = wish;
    this.ambient = ambient;
    this.palette = palettes[wish?.color] || palettes.gold;
    this.shape = !ambient && wish?.shape === "heart" ? "heart" : "burst";
    this.style = wish?.style || "velvet";
    this.profile = fireworkStyleProfile(this.style);
    this.x = width * (0.28 + Math.random() * 0.44);
    this.y = height * 0.92;
    this.targetY = this.shape === "heart"
      ? height * (0.3 + Math.random() * 0.13)
      : height * (0.19 + Math.random() * 0.31);
    this.targetX = this.x + (Math.random() - 0.5) * width * 0.12;
    this.vx = (this.targetX - this.x) / ASCENT_FRAMES;
    this.vy = (this.targetY - this.y) / ASCENT_FRAMES;
    this.life = 0;
    this.exploded = false;
    this.done = false;
  }

  update(frameScale = 1) {
    this.life += frameScale;
    if (!this.exploded) {
      const trailCount = Math.max(1, Math.round(frameScale));
      for (let i = 0; i < trailCount; i += 1) {
        particles.push(new Particle(
          this.x,
          this.y,
          (Math.random() - .5) * .6,
          1.3 + Math.random() * 1.4,
          this.palette[1],
          30,
          2.5,
          { gravity: .02, drag: .98, trailLength: 3, trailAlpha: .72 },
        ));
      }
      this.x += this.vx * frameScale;
      this.y += this.vy * frameScale;
      if (this.life >= ASCENT_FRAMES) this.explode();
      return;
    }
    if (this.life > FIREWORK_LIFETIME_FRAMES) this.done = true;
  }

  explode() {
    this.exploded = true;
    if (this.shape === "heart") this.explodeHeart();
    else if (this.style === "jewel") this.explodeJewelBurst();
    else if (this.style === "willow") this.explodeWillowBurst();
    else this.explodeVelvetBurst();
    this.addCoreSparks();
    if (!this.ambient && this.wish) {
      const labelY = this.shape === "heart" ? this.y + height * .13 : this.y;
      showWishLabel(this.wish, this.x, labelY);
    }
  }

  particle(vx, vy, color, life, size, options = {}) {
    particles.push(new Particle(this.x, this.y, vx, vy, color, life, size, {
      drag: this.profile.drag,
      gravity: this.profile.gravity,
      trailAlpha: this.profile.trailAlpha,
      ...options,
    }));
  }

  styleColor(index, accent = false) {
    if (this.style === "jewel") {
      const colors = [...this.palette, "#ffffff", "#70efff", "#ff83bc"];
      return colors[(index + (accent ? 2 : 0)) % colors.length];
    }
    if (this.style === "willow") {
      const colors = [...this.palette, "#ffd66f", "#ff9b4a", "#ff6652"];
      return colors[(index + (accent ? 1 : 0)) % colors.length];
    }
    const colors = [...this.palette, "#fff4c3", "#ffc45d"];
    return colors[(index + (accent ? 1 : 0)) % colors.length];
  }

  explodeVelvetBurst() {
    const count = this.ambient ? 78 : 126;
    for (let i = 0; i < count; i += 1) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - .5) * .035;
      const shell = i % 3 === 0 ? 1.05 : .72;
      const velocity = radialVelocity(angle, (3.8 + Math.random() * 2.5) * shell);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i), this.profile.particleLife * (.82 + Math.random() * .18), 2.2 + shell, {
        trailLength: 5,
        fadePower: .72,
      });
    }
    for (let i = 0; i < 42; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const velocity = radialVelocity(angle, 1.1 + Math.random() * 2.2, .15);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i, true), 205 + Math.random() * 70, 1.6, {
        gravity: .028,
        trailLength: 2,
        twinkle: true,
      });
    }
  }

  explodeJewelBurst() {
    const rays = this.ambient ? 68 : 108;
    for (let i = 0; i < rays; i += 1) {
      const angle = (Math.PI * 2 * i) / rays;
      const rayBoost = i % 4 === 0 ? 1.35 : .86;
      const velocity = radialVelocity(angle, (4.1 + Math.random() * 2.8) * rayBoost);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i), this.profile.particleLife * (.72 + Math.random() * .24), i % 4 === 0 ? 3.8 : 2.35, {
        trailLength: i % 4 === 0 ? 5 : 3,
        fadePower: .58,
      });
    }
    for (let i = 0; i < 36; i += 1) {
      const angle = (Math.PI * 2 * i) / 36 + .04;
      const velocity = radialVelocity(angle, 2 + Math.random() * 2.5);
      this.particle(velocity.vx, velocity.vy, i % 2 ? "#ffffff" : this.styleColor(i, true), 155 + Math.random() * 65, 2.8, {
        trailLength: 2,
        twinkle: true,
      });
    }
  }

  explodeWillowBurst() {
    const crown = this.ambient ? 72 : 116;
    for (let i = 0; i < crown; i += 1) {
      const angle = (Math.PI * 2 * i) / crown + (Math.random() - .5) * .04;
      const velocity = radialVelocity(angle, 3.5 + Math.random() * 2.8, .42);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i), this.profile.particleLife * (.84 + Math.random() * .16), 2.8 + Math.random() * 1.1, {
        gravity: .045 + Math.random() * .012,
        drag: .993,
        trailLength: 9,
        fadePower: .66,
      });
    }
    for (let i = 0; i < 34; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const velocity = radialVelocity(angle, .8 + Math.random() * 2, .65);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i, true), 250 + Math.random() * 90, 2.1, {
        gravity: .052,
        trailLength: 6,
        twinkle: true,
      });
    }
  }

  explodeHeart() {
    const pointsPerRing = this.style === "jewel" ? 84 : 76;
    const ringScales = this.style === "velvet" ? [.27, .36] : this.style === "willow" ? [.3, .39] : [.35];
    for (let ring = 0; ring < ringScales.length; ring += 1) {
      for (let i = 0; i < pointsPerRing; i += 1) {
        const angle = (Math.PI * 2 * i) / pointsPerRing;
        const velocity = heartVelocity(angle, ringScales[ring]);
        const willowBias = this.style === "willow" ? .35 : 0;
        this.particle(
          velocity.vx + (Math.random() - .5) * .1,
          velocity.vy + willowBias + (Math.random() - .5) * .1,
          this.styleColor(i + ring, ring > 0),
          this.profile.particleLife * (.84 + Math.random() * .16),
          this.style === "jewel" ? 3.45 : ring ? 3.2 : 2.55,
          {
            gravity: this.style === "willow" ? .045 : this.profile.gravity,
            trailLength: this.style === "willow" ? 8 : this.style === "velvet" ? 5 : 3,
            fadePower: this.style === "jewel" ? .58 : .7,
          },
        );
      }
    }
    const fillCount = this.style === "willow" ? 38 : 30;
    for (let i = 0; i < fillCount; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const speed = .7 + Math.random() * (this.style === "jewel" ? 3.1 : 2.2);
      const velocity = radialVelocity(angle, speed, this.style === "willow" ? .48 : .08);
      this.particle(velocity.vx, velocity.vy, this.styleColor(i, true), 175 + Math.random() * 95, this.style === "jewel" ? 2.8 : 2, {
        gravity: this.style === "willow" ? .05 : .027,
        trailLength: this.style === "willow" ? 7 : 2,
        twinkle: true,
      });
    }
  }

  addCoreSparks() {
    const sparkCount = this.shape === "heart" ? 16 : 28;
    for (let i = 0; i < sparkCount; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const speed = .6 + Math.random() * 1.7;
      const velocity = radialVelocity(angle, speed);
      this.particle(velocity.vx, velocity.vy, "#ffffff", 105 + Math.random() * 45, 4.2, {
        gravity: .018,
        drag: .978,
        trailLength: 2,
        twinkle: true,
      });
    }
  }

  draw() {
    if (this.exploded) return;
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.x, this.y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.shadowColor = this.palette[1];
    ctx.shadowBlur = 26;
    ctx.fill();
    ctx.restore();
  }
}

class Particle {
  constructor(x, y, vx, vy, color, life, size, options = {}) {
    this.x = x;
    this.y = y;
    this.px = x;
    this.py = y;
    this.vx = vx;
    this.vy = vy;
    this.color = color;
    this.life = life;
    this.maxLife = life;
    this.size = size;
    this.drag = options.drag ?? .985;
    this.gravity = options.gravity ?? .035;
    this.trailAlpha = options.trailAlpha ?? .82;
    this.trailLength = options.trailLength ?? 2;
    this.fadePower = options.fadePower ?? .74;
    this.twinkle = options.twinkle ?? false;
    this.twinklePhase = Math.random() * Math.PI * 2;
    this.trail = [{ x, y }];
  }

  update(frameScale = 1) {
    this.px = this.x;
    this.py = this.y;
    this.trail.unshift({ x: this.x, y: this.y });
    if (this.trail.length > this.trailLength) this.trail.length = this.trailLength;
    const drag = Math.pow(this.drag, frameScale);
    this.vx *= drag;
    this.vy = this.vy * drag + this.gravity * frameScale;
    this.x += this.vx * frameScale;
    this.y += this.vy * frameScale;
    this.life -= frameScale;
  }

  draw() {
    const progress = Math.max(0, this.life / this.maxLife);
    const shimmer = this.twinkle ? .55 + Math.sin(this.life * .18 + this.twinklePhase) * .45 : 1;
    const alpha = Math.pow(progress, this.fadePower) * this.trailAlpha * shimmer;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = this.color;
    ctx.lineWidth = Math.max(.9, this.size * (.35 + alpha * .9));
    ctx.lineCap = "round";
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 14 + this.size * 2.5;
    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    for (const point of this.trail) ctx.lineTo(point.x, point.y);
    ctx.stroke();
    ctx.globalAlpha = Math.min(1, alpha * 1.35);
    ctx.fillStyle = this.color;
    ctx.beginPath();
    ctx.arc(this.x, this.y, Math.max(.65, this.size * .28), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

function showWishLabel(wish, x, y) {
  const label = document.createElement("div");
  label.className = "wish-label";
  label.style.left = `${x}px`;
  label.style.top = `${Math.max(height * .2, y)}px`;
  label.style.color = palettes[wish.color]?.[0] || palettes.gold[0];
  const text = document.createElement("strong");
  text.textContent = wish.text;
  const author = document.createElement("small");
  author.textContent = `来自 ${wish.name}`;
  label.append(text, author);
  document.body.appendChild(label);
  setTimeout(() => label.remove(), 7000);
}

function animate(timestamp = 0) {
  const frameScale = previousFrame
    ? Math.min(Math.max((timestamp - previousFrame) / FRAME_MS, 0), 12)
    : 1;
  previousFrame = timestamp;
  if (rendererMode === "canvas") ctx.clearRect(0, 0, width, height);

  const playbackInterval = playbackQueue.hasPriority ? LAUNCH_INTERVAL_MS : WISH_LOOP_INTERVAL_MS;
  const readyForWish = history.length
    && timestamp - lastLaunch > playbackInterval
    && (rendererMode === "webgl" || active.length < 3);
  if (readyForWish) {
    const next = playbackQueue.next(history);
    if (next) launchWish(next.wish);
    lastLaunch = timestamp;
  }
  if (!history.length && timestamp - lastAmbient > AMBIENT_INTERVAL_MS && active.length === 0) {
    const colors = Object.keys(palettes);
    launchWish({ color: colors[Math.floor(Math.random() * colors.length)], style: "velvet" }, true);
    lastAmbient = timestamp;
  }

  if (rendererMode === "canvas") {
    for (const firework of active) {
      firework.update(frameScale);
      firework.draw();
    }
    for (const particle of particles) {
      particle.update(frameScale);
      particle.draw();
    }
    active = active.filter((item) => !item.done);
    particles = particles.filter((item) => item.life > 0).slice(-3600);
  }
  requestAnimationFrame(animate);
}
initializeRenderer();
requestAnimationFrame(animate);

function renderHistory() {
  historyList.replaceChildren();
  for (const wish of history.slice(0, 7)) {
    const item = document.createElement("article");
    item.className = "history-item";
    item.dataset.color = wish.color;
    const text = document.createElement("p");
    text.textContent = wish.text;
    const name = document.createElement("small");
    name.textContent = `✦ ${wish.name}`;
    item.append(text, name);
    historyList.appendChild(item);
  }
  wishCount.textContent = `${totalWishes || history.length} 条`;
}

function addWish(wish, { launch = true } = {}) {
  if (!wish || history.some((item) => item.id === wish.id)) return;
  history.unshift(wish);
  history = history.slice(0, 30);
  totalWishes += 1;
  renderHistory();
  if (launch) playbackQueue.enqueuePriority(wish);
}

function connect() {
  clearTimeout(reconnectTimer);
  socket = new WebSocket(wsUrl);
  socket.addEventListener("open", () => {
    statusDot.classList.add("online");
    connectionLabel.textContent = "互动进行中";
    socket.send(JSON.stringify({ type: "join", room, role: "display", clientId: `display-${room}` }));
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "joined") {
      history = message.history || [];
      totalWishes = history.length;
      applyConfig(message.config);
      renderHistory();
    }
    if (message.type === "config") applyConfig(message.config);
    if (message.type === "history-cleared") {
      history = [];
      totalWishes = 0;
      playbackQueue.clear();
      webglRenderer?.clear();
      active = [];
      particles = [];
      document.querySelectorAll(".wish-label").forEach((label) => label.remove());
      renderHistory();
    }
    if (message.type === "wish") addWish(message.wish);
    if (message.type === "stats") participantCount.textContent = message.participantCount || 0;
  });
  socket.addEventListener("close", () => {
    statusDot.classList.remove("online");
    connectionLabel.textContent = "正在重连";
    reconnectTimer = setTimeout(connect, 1600);
  });
  socket.addEventListener("error", () => socket.close());
}

connect();
