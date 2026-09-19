import assert from "node:assert/strict";
import test from "node:test";

import { fireworkStyleProfile, heartVelocity, radialVelocity } from "../public/firework-geometry.js";

test("firework style profiles define longer bounded lifetimes", () => {
  assert.equal(fireworkStyleProfile("velvet").particleLife, 300);
  assert.equal(fireworkStyleProfile("jewel").particleLife, 270);
  assert.equal(fireworkStyleProfile("willow").particleLife, 360);
  assert.deepEqual(fireworkStyleProfile("unknown"), fireworkStyleProfile("velvet"));
  assert.ok(fireworkStyleProfile("willow").gravity > fireworkStyleProfile("jewel").gravity);
});

test("radial velocity follows its angle and supports downward bias", () => {
  assert.deepEqual(radialVelocity(0, 4), { vx: 4, vy: 0 });
  const downward = radialVelocity(Math.PI / 2, 3, 1.2);
  assert.ok(Math.abs(downward.vx) < 1e-9);
  assert.ok(Math.abs(downward.vy - 4.2) < 1e-9);
});

test("heart outline has symmetric lobes, a top notch, and a lower tip", () => {
  const scale = 0.36;
  const notch = heartVelocity(0, scale);
  const right = heartVelocity(Math.PI / 2, scale);
  const tip = heartVelocity(Math.PI, scale);
  const left = heartVelocity(Math.PI * 1.5, scale);

  assert.ok(Math.abs(notch.vx) < 1e-9);
  assert.ok(Math.abs(tip.vx) < 1e-9);
  assert.ok(right.vx > 5);
  assert.ok(left.vx < -5);
  assert.ok(Math.abs(right.vx + left.vx) < 1e-9);
  assert.ok(Math.abs(right.vy - left.vy) < 1e-9);
  assert.ok(notch.vy < 0);
  assert.ok(tip.vy > 5);
  assert.ok(tip.vy - notch.vy > 7);
});
