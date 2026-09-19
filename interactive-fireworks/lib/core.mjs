export const ROOM_PATTERN = /^[a-z0-9][a-z0-9-]{0,31}$/;
export const COLORS = new Set(["gold", "rose", "cyan", "violet", "emerald"]);
export const FIREWORK_SHAPES = new Set(["burst", "heart"]);
export const FIREWORK_STYLES = new Set(["velvet", "jewel", "willow"]);

const DEFAULT_BLOCKED_WORDS = ["赌博", "博彩", "诈骗", "色情", "毒品", "傻逼", "滚蛋"];

export function normalizeRoom(value) {
  const room = String(value || "lobby").trim().toLowerCase();
  return ROOM_PATTERN.test(room) ? room : null;
}

export function normalizeWish(input, options = {}) {
  const normalizedOptions = Array.isArray(options) ? { blockedWords: options } : options;
  const blockedWords = normalizedOptions.blockedWords || DEFAULT_BLOCKED_WORDS;
  const maxWishLength = normalizedOptions.maxWishLength || 28;
  const maxNameLength = normalizedOptions.maxNameLength || 8;
  const text = String(input?.text || "").replace(/\s+/g, " ").trim();
  const requestedName = String(input?.name || "").replace(/\s+/g, " ").trim();
  const name = requestedName || "神秘来宾";
  const color = COLORS.has(input?.color) ? input.color : "gold";
  const shape = FIREWORK_SHAPES.has(input?.shape) ? input.shape : "burst";
  const style = FIREWORK_STYLES.has(input?.style) ? input.style : "velvet";

  if (!text || text.length > maxWishLength) {
    return { ok: false, error: `祝福语需为 1—${maxWishLength} 个字符` };
  }
  if (requestedName.length > maxNameLength) {
    return { ok: false, error: `昵称不能超过 ${maxNameLength} 个字符` };
  }
  const matched = blockedWords.find((word) => text.includes(word) || name.includes(word));
  if (matched) {
    return { ok: false, error: "内容包含不适合公开展示的词语" };
  }

  return {
    ok: true,
    value: {
      text,
      name: name || "神秘来宾",
      color,
      shape,
      style,
    },
  };
}

export function safeJsonParse(raw) {
  try {
    return JSON.parse(String(raw));
  } catch {
    return null;
  }
}

export class SlidingWindowLimiter {
  constructor({ limit = 3, windowMs = 30_000 } = {}) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.entries = new Map();
  }

  allow(key, now = Date.now()) {
    const recent = (this.entries.get(key) || []).filter((time) => now - time < this.windowMs);
    if (recent.length >= this.limit) {
      this.entries.set(key, recent);
      return false;
    }
    recent.push(now);
    this.entries.set(key, recent);
    return true;
  }
}
