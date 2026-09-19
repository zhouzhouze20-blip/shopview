import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import Database from "better-sqlite3";
import express from "express";
import QRCode from "qrcode";
import { WebSocketServer, WebSocket } from "ws";

import { activityConfigFromRow, activityConfigToRow, normalizeActivityConfig } from "./lib/activity-config.mjs";
import { SlidingWindowLimiter, normalizeRoom, normalizeWish, safeJsonParse } from "./lib/core.mjs";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.join(rootDir, "data");
fs.mkdirSync(dataDir, { recursive: true });

const port = Number(process.env.PORT || 8787);
const publicBaseUrl = process.env.PUBLIC_BASE_URL?.replace(/\/$/, "");
const databasePath = process.env.DATABASE_PATH || path.join(dataDir, "wishes.db");
const adminToken = process.env.ADMIN_TOKEN || "";
const appVersion = process.env.APP_VERSION || "0.2.2";

const db = new Database(databasePath);
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS wishes (
    id TEXT PRIMARY KEY,
    room TEXT NOT NULL,
    text TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    shape TEXT NOT NULL DEFAULT 'burst',
    style TEXT NOT NULL DEFAULT 'velvet',
    status TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    approved_at INTEGER
  );
  CREATE INDEX IF NOT EXISTS wishes_room_status_time
    ON wishes (room, status, created_at DESC);
  CREATE TABLE IF NOT EXISTS activity_configs (
    room TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    display_kicker TEXT NOT NULL,
    display_title TEXT NOT NULL,
    idle_title TEXT NOT NULL,
    idle_subtitle TEXT NOT NULL,
    mobile_title TEXT NOT NULL,
    mobile_subtitle TEXT NOT NULL,
    templates_json TEXT NOT NULL,
    submissions_enabled INTEGER NOT NULL,
    max_wish_length INTEGER NOT NULL,
    max_name_length INTEGER NOT NULL,
    blocked_words_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
  );
`);

const wishColumns = new Set(db.prepare("PRAGMA table_info(wishes)").all().map((column) => column.name));
if (!wishColumns.has("shape")) {
  db.exec("ALTER TABLE wishes ADD COLUMN shape TEXT NOT NULL DEFAULT 'burst'");
}
if (!wishColumns.has("style")) {
  db.exec("ALTER TABLE wishes ADD COLUMN style TEXT NOT NULL DEFAULT 'velvet'");
}

const insertWish = db.prepare(`
  INSERT INTO wishes (id, room, text, name, color, shape, style, status, created_at, approved_at)
  VALUES (@id, @room, @text, @name, @color, @shape, @style, @status, @createdAt, @approvedAt)
`);
const historyQuery = db.prepare(`
  SELECT id, room, text, name, color, shape, style, created_at AS createdAt, approved_at AS approvedAt
  FROM wishes
  WHERE room = ? AND status = 'approved'
  ORDER BY COALESCE(approved_at, created_at) DESC
  LIMIT ?
`);
const wishCountQuery = db.prepare(`SELECT COUNT(*) AS count FROM wishes WHERE room = ? AND status = 'approved'`);
const deleteWishes = db.prepare(`DELETE FROM wishes WHERE room = ?`);
const healthQuery = db.prepare(`SELECT 1 AS ok`);
const activityConfigQuery = db.prepare(`SELECT * FROM activity_configs WHERE room = ?`);
const upsertActivityConfig = db.prepare(`
  INSERT INTO activity_configs (
    room, brand, display_kicker, display_title, idle_title, idle_subtitle,
    mobile_title, mobile_subtitle, templates_json, submissions_enabled,
    max_wish_length, max_name_length, blocked_words_json, updated_at
  ) VALUES (
    @room, @brand, @displayKicker, @displayTitle, @idleTitle, @idleSubtitle,
    @mobileTitle, @mobileSubtitle, @templatesJson, @submissionsEnabled,
    @maxWishLength, @maxNameLength, @blockedWordsJson, @updatedAt
  )
  ON CONFLICT(room) DO UPDATE SET
    brand = excluded.brand,
    display_kicker = excluded.display_kicker,
    display_title = excluded.display_title,
    idle_title = excluded.idle_title,
    idle_subtitle = excluded.idle_subtitle,
    mobile_title = excluded.mobile_title,
    mobile_subtitle = excluded.mobile_subtitle,
    templates_json = excluded.templates_json,
    submissions_enabled = excluded.submissions_enabled,
    max_wish_length = excluded.max_wish_length,
    max_name_length = excluded.max_name_length,
    blocked_words_json = excluded.blocked_words_json,
    updated_at = excluded.updated_at
`);

function getActivityConfig(room) {
  return activityConfigFromRow(activityConfigQuery.get(room));
}

function saveActivityConfig(room, input) {
  const config = normalizeActivityConfig(input, getActivityConfig(room));
  upsertActivityConfig.run(activityConfigToRow(room, config));
  return config;
}
const app = express();
app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(express.json({ limit: "16kb" }));
app.use("/vendor/three", express.static(path.join(rootDir, "node_modules", "three"), {
  fallthrough: false,
  immutable: true,
  maxAge: "1y",
}));
app.use(express.static(path.join(rootDir, "public"), { extensions: ["html"] }));

function requestBaseUrl(req) {
  if (publicBaseUrl) return publicBaseUrl;
  const protocol = req.get("x-forwarded-proto") || req.protocol;
  return `${protocol}://${req.get("host")}`;
}

app.get("/", (_req, res) => res.redirect("/display.html?room=lobby"));

app.get("/healthz", (_req, res, next) => {
  try {
    healthQuery.get();
    res.json({ status: "ok", service: "interactive-fireworks", version: appVersion });
  } catch (error) {
    next(error);
  }
});

app.get("/api/rooms/:room", (req, res) => {
  const room = normalizeRoom(req.params.room);
  if (!room) return res.status(400).json({ error: "活动场次无效" });
  const history = historyQuery.all(room, 30);
  res.json({
    room,
    history,
    config: getActivityConfig(room),
    joinUrl: `${requestBaseUrl(req)}/join.html?room=${encodeURIComponent(room)}`,
  });
});

app.get("/api/rooms/:room/qr.svg", async (req, res, next) => {
  try {
    const room = normalizeRoom(req.params.room);
    if (!room) return res.status(400).send("invalid room");
    const joinUrl = `${requestBaseUrl(req)}/join.html?room=${encodeURIComponent(room)}`;
    const svg = await QRCode.toString(joinUrl, {
      type: "svg",
      margin: 1,
      color: { dark: "#08102D", light: "#FFFFFF" },
      errorCorrectionLevel: "M",
    });
    res.type("image/svg+xml").send(svg);
  } catch (error) {
    next(error);
  }
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws", maxPayload: 16 * 1024 });
const limiter = new SlidingWindowLimiter({ limit: 3, windowMs: 30_000 });
const clients = new Set();

function roomStats(room) {
  let displayCount = 0;
  let participantCount = 0;
  for (const client of clients) {
    if (client.readyState !== WebSocket.OPEN || client.meta?.room !== room) continue;
    if (client.meta.role === "display") displayCount += 1;
    if (client.meta.role === "mobile") participantCount += 1;
  }
  return { displayCount, participantCount };
}

function send(client, payload) {
  if (client.readyState === WebSocket.OPEN) client.send(JSON.stringify(payload));
}

function broadcastRoom(room, payload) {
  for (const client of clients) {
    if (client.meta?.room === room) send(client, payload);
  }
}

function connectionKey(req, clientId) {
  return `${req.socket.remoteAddress || "unknown"}:${String(clientId || "anon").slice(0, 64)}`;
}

function requireAdmin(req, res, next) {
  if (!adminToken) {
    return res.status(503).json({ error: "管理员令牌未配置，请设置 ADMIN_TOKEN 后重启服务" });
  }
  const supplied = Buffer.from(String(req.get("x-admin-token") || ""));
  const expected = Buffer.from(adminToken);
  if (supplied.length !== expected.length || !crypto.timingSafeEqual(supplied, expected)) {
    return res.status(401).json({ error: "管理员令牌无效" });
  }
  next();
}

app.get("/api/admin/rooms/:room", requireAdmin, (req, res) => {
  const room = normalizeRoom(req.params.room);
  if (!room) return res.status(400).json({ error: "活动场次无效" });
  res.json({
    room,
    config: getActivityConfig(room),
    stats: {
      ...roomStats(room),
      wishCount: wishCountQuery.get(room).count,
    },
    links: {
      display: `${requestBaseUrl(req)}/display.html?room=${encodeURIComponent(room)}`,
      join: `${requestBaseUrl(req)}/join.html?room=${encodeURIComponent(room)}`,
    },
  });
});

app.put("/api/admin/rooms/:room", requireAdmin, (req, res) => {
  const room = normalizeRoom(req.params.room);
  if (!room) return res.status(400).json({ error: "活动场次无效" });
  const config = saveActivityConfig(room, req.body?.config || req.body || {});
  broadcastRoom(room, { type: "config", config });
  res.json({ room, config, message: "活动配置已保存并实时生效" });
});

app.delete("/api/admin/rooms/:room/wishes", requireAdmin, async (req, res, next) => {
  try {
    const room = normalizeRoom(req.params.room);
    if (!room) return res.status(400).json({ error: "活动场次无效" });
    const backupDir = path.join(path.dirname(databasePath), "backups");
    fs.mkdirSync(backupDir, { recursive: true });
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const backupPath = path.join(backupDir, `${room}-before-clear-${timestamp}.db`);
    await db.backup(backupPath);
    const result = deleteWishes.run(room);
    broadcastRoom(room, { type: "history-cleared" });
    res.json({
      room,
      deleted: result.changes,
      backupFile: path.basename(backupPath),
      message: `已清空 ${result.changes} 条祝福`,
    });
  } catch (error) {
    next(error);
  }
});

wss.on("connection", (socket, req) => {
  socket.isAlive = true;
  socket.meta = null;
  clients.add(socket);

  socket.on("pong", () => { socket.isAlive = true; });
  socket.on("message", (raw) => {
    const message = safeJsonParse(raw);
    if (!message) return send(socket, { type: "error", message: "消息格式错误" });

    if (message.type === "join") {
      const room = normalizeRoom(message.room);
      const role = ["display", "mobile"].includes(message.role) ? message.role : null;
      if (!room || !role) return send(socket, { type: "error", message: "活动场次无效" });
      socket.meta = { room, role, clientId: String(message.clientId || "") };
      send(socket, { type: "joined", room, history: historyQuery.all(room, 30), config: getActivityConfig(room) });
      broadcastRoom(room, { type: "stats", ...roomStats(room) });
      return;
    }

    if (message.type === "submit") {
      if (!socket.meta || socket.meta.role !== "mobile") {
        return send(socket, { type: "error", message: "请先扫码进入活动" });
      }
      const config = getActivityConfig(socket.meta.room);
      if (!config.submissionsEnabled) {
        return send(socket, { type: "error", requestId: message.requestId, message: "活动暂未开放祝福提交" });
      }
      const key = connectionKey(req, socket.meta.clientId);
      if (!limiter.allow(key)) {
        return send(socket, { type: "error", requestId: message.requestId, message: "发射太频繁，请稍后再试" });
      }
      const normalized = normalizeWish(message, config);
      if (!normalized.ok) {
        return send(socket, { type: "error", requestId: message.requestId, message: normalized.error });
      }
      const createdAt = Date.now();
      const wish = {
        id: crypto.randomUUID(),
        room: socket.meta.room,
        ...normalized.value,
        status: "approved",
        createdAt,
        approvedAt: createdAt,
      };
      insertWish.run(wish);
      send(socket, {
        type: "accepted",
        requestId: message.requestId,
        wish,
        message: "烟花已发往大屏",
      });
      broadcastRoom(socket.meta.room, { type: "wish", wish });
      broadcastRoom(socket.meta.room, { type: "stats", ...roomStats(socket.meta.room) });
    }
  });

  socket.on("close", () => {
    const room = socket.meta?.room;
    clients.delete(socket);
    if (room) broadcastRoom(room, { type: "stats", ...roomStats(room) });
  });
});

const heartbeat = setInterval(() => {
  for (const socket of clients) {
    if (!socket.isAlive) {
      socket.terminate();
      continue;
    }
    socket.isAlive = false;
    socket.ping();
  }
}, 25_000);

server.on("close", () => {
  clearInterval(heartbeat);
  db.close();
});

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(500).json({ error: "服务暂时不可用" });
});

if (process.env.NODE_ENV !== "test") {
  server.listen(port, "0.0.0.0", () => {
    console.log(`Interactive Fireworks: http://localhost:${port}/display.html?room=lobby`);
    console.log(`Mobile page:          http://localhost:${port}/join.html?room=lobby`);
  });

  let shuttingDown = false;
  const shutdown = (signal) => {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log(`${signal} received, shutting down Interactive Fireworks...`);

    const forceExit = setTimeout(() => {
      console.error("Graceful shutdown timed out");
      process.exit(1);
    }, 10_000);
    forceExit.unref();

    for (const socket of clients) socket.close(1001, "server shutdown");
    wss.close();
    server.close((error) => {
      clearTimeout(forceExit);
      if (error) {
        console.error(error);
        process.exit(1);
      }
      process.exit(0);
    });
    server.closeIdleConnections?.();
  };

  process.once("SIGTERM", () => shutdown("SIGTERM"));
  process.once("SIGINT", () => shutdown("SIGINT"));
}

export { app, server, db };
