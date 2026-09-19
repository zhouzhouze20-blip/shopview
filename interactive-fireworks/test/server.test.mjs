import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import Database from "better-sqlite3";
import WebSocket from "ws";

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "interactive-fireworks-test-"));
process.env.NODE_ENV = "test";
process.env.DATABASE_PATH = path.join(tempDir, "wishes.db");
process.env.ADMIN_TOKEN = "test-admin-token";

const legacyDb = new Database(process.env.DATABASE_PATH);
legacyDb.exec(`
  CREATE TABLE wishes (
    id TEXT PRIMARY KEY,
    room TEXT NOT NULL,
    text TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    approved_at INTEGER
  );
`);
legacyDb.close();

const { server } = await import("../server.mjs");

function waitForMessage(socket, predicate, timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      socket.off("message", onMessage);
      reject(new Error("WebSocket message timeout"));
    }, timeoutMs);
    function onMessage(raw) {
      const message = JSON.parse(raw);
      if (!predicate(message)) return;
      clearTimeout(timer);
      socket.off("message", onMessage);
      resolve(message);
    }
    socket.on("message", onMessage);
  });
}

async function closeSocket(socket) {
  if (!socket || socket.readyState === WebSocket.CLOSED) return;
  await new Promise((resolve) => {
    socket.once("close", resolve);
    socket.terminate();
  });
}

test("admin configuration is protected, persisted, and broadcast", async () => {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const wsUrl = `ws://127.0.0.1:${address.port}/ws`;
  const display = new WebSocket(wsUrl);
  const displayOpened = new Promise((resolve, reject) => {
    display.once("open", resolve);
    display.once("error", reject);
  });
  let mobile;

  try {
    const healthResponse = await fetch(`${baseUrl}/healthz`);
    assert.equal(healthResponse.status, 200);
    assert.deepEqual(await healthResponse.json(), {
      status: "ok",
      service: "interactive-fireworks",
      version: "0.2.2",
    });

    const threeModuleResponse = await fetch(`${baseUrl}/vendor/three/build/three.module.js`);
    assert.equal(threeModuleResponse.status, 200);
    assert.match(threeModuleResponse.headers.get("content-type") || "", /javascript/);
    assert.match((await threeModuleResponse.text()).slice(0, 400), /Three\.js|REVISION|const REVISION/);

    const publicResponse = await fetch(`${baseUrl}/api/rooms/demo`);
    assert.equal(publicResponse.status, 200);
    const publicRoom = await publicResponse.json();
    assert.equal(publicRoom.config.brand, "星河心愿");

    const unauthorized = await fetch(`${baseUrl}/api/admin/rooms/demo`);
    assert.equal(unauthorized.status, 401);

    await displayOpened;
    display.send(JSON.stringify({ type: "join", room: "demo", role: "display", clientId: "test-display" }));
    const joined = await waitForMessage(display, (message) => message.type === "joined");
    assert.equal(joined.config.displayTitle, "让每一句祝福，都在星空绽放");

    mobile = new WebSocket(wsUrl);
    await new Promise((resolve, reject) => {
      mobile.once("open", resolve);
      mobile.once("error", reject);
    });
    mobile.send(JSON.stringify({ type: "join", room: "demo", role: "mobile", clientId: "test-mobile" }));
    await waitForMessage(mobile, (message) => message.type === "joined");
    const acceptedPromise = waitForMessage(mobile, (message) => message.type === "accepted");
    const wishBroadcastPromise = waitForMessage(display, (message) => message.type === "wish");
    mobile.send(JSON.stringify({
      type: "submit",
      requestId: "heart-test",
      text: "心愿成真",
      name: "测试来宾",
      color: "rose",
      shape: "heart",
      style: "willow",
    }));
    const [accepted, wishBroadcast] = await Promise.all([acceptedPromise, wishBroadcastPromise]);
    assert.equal(accepted.wish.shape, "heart");
    assert.equal(wishBroadcast.wish.shape, "heart");
    assert.equal(accepted.wish.style, "willow");
    assert.equal(wishBroadcast.wish.style, "willow");
    const historyAfterSubmit = await (await fetch(`${baseUrl}/api/rooms/demo`)).json();
    assert.equal(historyAfterSubmit.history[0].shape, "heart");
    assert.equal(historyAfterSubmit.history[0].style, "willow");

    const configMessagePromise = waitForMessage(display, (message) => message.type === "config");
    const updateResponse = await fetch(`${baseUrl}/api/admin/rooms/demo`, {
      method: "PUT",
      headers: { "content-type": "application/json", "x-admin-token": "test-admin-token" },
      body: JSON.stringify({
        config: {
          brand: "测试活动",
          displayTitle: "测试烟花夜",
          templates: ["测试祝福"],
          submissionsEnabled: false,
          maxWishLength: 16,
          maxNameLength: 6,
          blockedWords: ["禁止词"],
        },
      }),
    });
    assert.equal(updateResponse.status, 200);
    const update = await updateResponse.json();
    assert.equal(update.config.brand, "测试活动");
    assert.equal(update.config.submissionsEnabled, false);

    const broadcast = await configMessagePromise;
    assert.equal(broadcast.config.displayTitle, "测试烟花夜");

    const partialUpdateResponse = await fetch(`${baseUrl}/api/admin/rooms/demo`, {
      method: "PUT",
      headers: { "content-type": "application/json", "x-admin-token": "test-admin-token" },
      body: JSON.stringify({ config: { idleTitle: "部分更新" } }),
    });
    const partialUpdate = await partialUpdateResponse.json();
    assert.equal(partialUpdate.config.brand, "测试活动");
    assert.equal(partialUpdate.config.idleTitle, "部分更新");

    const persisted = await (await fetch(`${baseUrl}/api/rooms/demo`)).json();
    assert.equal(persisted.config.maxWishLength, 16);
    assert.deepEqual(persisted.config.blockedWords, ["禁止词"]);

    const clearResponse = await fetch(`${baseUrl}/api/admin/rooms/demo/wishes`, {
      method: "DELETE",
      headers: { "x-admin-token": "test-admin-token" },
    });
    assert.equal(clearResponse.status, 200);
    const cleared = await clearResponse.json();
    assert.equal(cleared.deleted, 1);
    assert.equal(fs.existsSync(path.join(tempDir, "backups", cleared.backupFile)), true);
  } finally {
    await Promise.all([closeSocket(mobile), closeSocket(display)]);
    server.closeAllConnections?.();
    await new Promise((resolve) => server.close(resolve));
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
