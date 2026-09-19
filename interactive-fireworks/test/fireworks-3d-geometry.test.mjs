import assert from "node:assert/strict";
import test from "node:test";

import {
  createQualityController,
  QUALITY_TIERS,
  sampleHeartVolume,
  sampleSphere,
  seededRandom,
} from "../public/fireworks-3d-geometry.js";

test("samples a full three-dimensional sphere", () => {
  const points = sampleSphere(256, seededRandom(7));
  assert.equal(points.length, 256);
  assert.ok(points.some((point) => point.z > .5));
  assert.ok(points.some((point) => point.z < -.5));
  assert.ok(points.some((point) => point.x > .8));
  assert.ok(points.some((point) => point.x < -.8));
});

test("samples a recognizable heart volume with front and back depth", () => {
  const points = sampleHeartVolume(360, seededRandom(9));
  assert.ok(Math.min(...points.map((point) => point.y)) < -.7);
  assert.ok(points.some((point) => point.x > .7 && point.y > .05));
  assert.ok(points.some((point) => point.x < -.7 && point.y > .05));
  assert.ok(points.some((point) => point.z > .1));
  assert.ok(points.some((point) => point.z < -.1));
});

test("adaptive quality steps down and requests fallback at sustained critical fps", () => {
  const controller = createQualityController("high");
  assert.equal(controller.profile.particles, QUALITY_TIERS.high.particles);
  controller.observe(35);
  assert.equal(controller.observe(35).tier, "medium");
  controller.observe(20);
  assert.equal(controller.observe(20).tier, "low");
  assert.equal(controller.observe(20).fallback, true);
});
