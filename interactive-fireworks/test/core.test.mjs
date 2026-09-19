import test from "node:test";
import assert from "node:assert/strict";

import { SlidingWindowLimiter, normalizeRoom, normalizeWish, safeJsonParse } from "../lib/core.mjs";
import { activityConfigFromRow, activityConfigToRow, normalizeActivityConfig } from "../lib/activity-config.mjs";
import { createClientId } from "../public/client-id.js";

test("normalizes a valid wish and applies defaults", () => {
  const result = normalizeWish({ text: "  平安   喜乐  ", color: "cyan" });
  assert.equal(result.ok, true);
  assert.deepEqual(result.value, { text: "平安 喜乐", name: "神秘来宾", color: "cyan", shape: "burst", style: "velvet" });
  assert.equal(normalizeWish({ text: "心愿成真", shape: "heart" }).value.shape, "heart");
  assert.equal(normalizeWish({ text: "心愿成真", shape: "star" }).value.shape, "burst");
  assert.equal(normalizeWish({ text: "心愿成真", style: "willow" }).value.style, "willow");
  assert.equal(normalizeWish({ text: "心愿成真", style: "unknown" }).value.style, "velvet");
});

test("rejects overlong and blocked public content", () => {
  assert.equal(normalizeWish({ text: "愿".repeat(29) }).ok, false);
  assert.equal(normalizeWish({ text: "参与赌博" }).ok, false);
  assert.equal(normalizeWish({ text: "新年快乐", name: "名".repeat(9) }).ok, false);
});

test("validates room slugs", () => {
  assert.equal(normalizeRoom(" New-Year-2027 "), "new-year-2027");
  assert.equal(normalizeRoom("../bad"), null);
  assert.equal(normalizeRoom("中文场次"), null);
});

test("safeJsonParse returns null for malformed messages", () => {
  assert.deepEqual(safeJsonParse('{"type":"join"}'), { type: "join" });
  assert.equal(safeJsonParse("{"), null);
});

test("sliding window limiter expires old events", () => {
  const limiter = new SlidingWindowLimiter({ limit: 2, windowMs: 1000 });
  assert.equal(limiter.allow("a", 0), true);
  assert.equal(limiter.allow("a", 100), true);
  assert.equal(limiter.allow("a", 200), false);
  assert.equal(limiter.allow("a", 1100), true);
});

test("creates UUID-shaped ids when randomUUID is unavailable", () => {
  let value = 0;
  const cryptoApi = {
    getRandomValues(bytes) {
      for (let index = 0; index < bytes.length; index += 1) {
        bytes[index] = value++;
      }
      return bytes;
    },
  };

  const id = createClientId(cryptoApi);
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test("normalizes activity configuration and enforces limits", () => {
  const config = normalizeActivityConfig({
    brand: "  商场周年庆  ",
    templates: ["生日快乐", "生日快乐", "阖家幸福"],
    maxWishLength: 200,
    maxNameLength: 0,
    submissionsEnabled: false,
  });
  assert.equal(config.brand, "商场周年庆");
  assert.deepEqual(config.templates, ["生日快乐", "阖家幸福"]);
  assert.equal(config.maxWishLength, 80);
  assert.equal(config.maxNameLength, 1);
  assert.equal(config.submissionsEnabled, false);
  assert.deepEqual(normalizeActivityConfig({ blockedWords: [] }).blockedWords, []);
});

test("round-trips activity configuration through database rows", () => {
  const row = activityConfigToRow("lobby", { displayTitle: "周年庆烟花夜", blockedWords: ["测试词"] }, 123);
  const restored = activityConfigFromRow({
    room: row.room,
    brand: row.brand,
    display_kicker: row.displayKicker,
    display_title: row.displayTitle,
    idle_title: row.idleTitle,
    idle_subtitle: row.idleSubtitle,
    mobile_title: row.mobileTitle,
    mobile_subtitle: row.mobileSubtitle,
    templates_json: row.templatesJson,
    submissions_enabled: row.submissionsEnabled,
    max_wish_length: row.maxWishLength,
    max_name_length: row.maxNameLength,
    blocked_words_json: row.blockedWordsJson,
    updated_at: row.updatedAt,
  });
  assert.equal(restored.displayTitle, "周年庆烟花夜");
  assert.deepEqual(restored.blockedWords, ["测试词"]);
});

test("applies room-specific wish limits", () => {
  assert.equal(normalizeWish({ text: "六个字符祝福" }, { maxWishLength: 5 }).ok, false);
  assert.equal(normalizeWish({ text: "祝福", name: "四字名字" }, { maxNameLength: 3 }).ok, false);
  assert.equal(normalizeWish({ text: "禁止内容" }, { blockedWords: ["禁止"] }).ok, false);
  assert.deepEqual(normalizeWish({ text: "祝福" }, { maxNameLength: 1 }).value.name, "神秘来宾");
});
