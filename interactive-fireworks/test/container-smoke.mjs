import assert from "node:assert/strict";

import WebSocket from "ws";

const baseUrl = (process.env.SMOKE_BASE_URL || "http://127.0.0.1:18787").replace(/\/$/, "");
const adminToken = process.env.SMOKE_ADMIN_TOKEN || "";
const room = `smoke-${Date.now()}`;
const wsUrl = `${baseUrl.replace(/^http/, "ws")}/ws`;

function waitForMessage(socket, predicate, timeoutMs = 5_000) {
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

async function join(role) {
  const socket = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    socket.once("open", resolve);
    socket.once("error", reject);
  });
  const joinedPromise = waitForMessage(socket, (message) => message.type === "joined");
  socket.send(JSON.stringify({ type: "join", room, role, clientId: `smoke-${role}` }));
  await joinedPromise;
  return socket;
}

const healthResponse = await fetch(`${baseUrl}/healthz`);
assert.equal(healthResponse.status, 200);
assert.equal((await healthResponse.json()).status, "ok");

const roomResponse = await fetch(`${baseUrl}/api/rooms/${room}`);
assert.equal(roomResponse.status, 200);
assert.equal((await roomResponse.json()).joinUrl, `${baseUrl}/join.html?room=${room}`);

if (adminToken) {
  const adminResponse = await fetch(`${baseUrl}/api/admin/rooms/${room}`, {
    headers: { "x-admin-token": adminToken },
  });
  assert.equal(adminResponse.status, 200);
}

const display = await join("display");
const mobile = await join("mobile");

try {
  const requestId = `smoke-${Date.now()}`;
  const acceptedPromise = waitForMessage(
    mobile,
    (message) => message.type === "accepted" && message.requestId === requestId,
  );
  const wishPromise = waitForMessage(
    display,
    (message) => message.type === "wish" && message.wish?.text === "Docker部署测试成功",
  );

  mobile.send(JSON.stringify({
    type: "submit",
    requestId,
    text: "Docker部署测试成功",
    name: "冒烟测试",
    color: "gold",
  }));

  const [accepted, broadcast] = await Promise.all([acceptedPromise, wishPromise]);
  assert.equal(accepted.wish.id, broadcast.wish.id);
  console.log(`Container smoke test passed: room=${room} wish=${accepted.wish.id}`);
} finally {
  display.close();
  mobile.close();
}
