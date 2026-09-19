import assert from "node:assert/strict";
import test from "node:test";

import { createWishPlaybackQueue } from "../public/wish-playback.js";

const a = { id: "a", text: "祝福 A" };
const b = { id: "b", text: "祝福 B" };
const c = { id: "c", text: "祝福 C" };

test("loops through every historical wish continuously", () => {
  const queue = createWishPlaybackQueue();

  assert.equal(queue.next([a, b]).wish, a);
  assert.equal(queue.next([a, b]).wish, b);
  assert.equal(queue.next([a, b]).wish, a);
  assert.equal(queue.next([a, b]).wish, b);
});

test("plays new wishes before continuing the current history cycle", () => {
  const queue = createWishPlaybackQueue();

  assert.equal(queue.next([a, b]).wish, a);
  queue.enqueuePriority(c);
  assert.equal(queue.hasPriority, true);
  assert.deepEqual(queue.next([c, a, b]), { wish: c, source: "priority" });
  assert.equal(queue.next([c, a, b]).wish, b);
  assert.equal(queue.next([c, a, b]).wish, c);
});

test("clearing playback removes pending and replay wishes", () => {
  const queue = createWishPlaybackQueue();
  queue.enqueuePriority(c);
  queue.clear();

  assert.equal(queue.hasPriority, false);
  assert.equal(queue.next([]), null);
});
