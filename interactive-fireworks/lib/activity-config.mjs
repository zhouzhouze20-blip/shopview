export const DEFAULT_ACTIVITY_CONFIG = Object.freeze({
  brand: "星河心愿",
  displayKicker: "MAKE A WISH · LIGHT THE NIGHT",
  displayTitle: "让每一句祝福，都在星空绽放",
  idleTitle: "此刻，星空正在等待你的心愿",
  idleSubtitle: "扫描左侧二维码，发射专属烟花",
  mobileTitle: "写下此刻的祝福",
  mobileSubtitle: "向上滑动，让心愿在现场大屏绽放",
  templates: ["万事顺遂，平安喜乐", "所愿皆所得，所行皆坦途", "新岁启封，好运常在"],
  submissionsEnabled: true,
  maxWishLength: 28,
  maxNameLength: 8,
  blockedWords: ["赌博", "博彩", "诈骗", "色情", "毒品", "傻逼", "滚蛋"],
});

function clampInteger(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isInteger(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function cleanText(value, fallback, maxLength) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  return (text || fallback).slice(0, maxLength);
}

function cleanList(value, fallback, { maxItems, maxLength, allowEmpty = false }) {
  const source = Array.isArray(value) ? value : fallback;
  const unique = [];
  for (const item of source) {
    const text = String(item ?? "").replace(/\s+/g, " ").trim().slice(0, maxLength);
    if (text && !unique.includes(text)) unique.push(text);
    if (unique.length >= maxItems) break;
  }
  return unique.length || allowEmpty ? unique : [...fallback];
}

function parseList(value, fallback) {
  try {
    const parsed = JSON.parse(value || "[]");
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function normalizeActivityConfig(input = {}, fallback = DEFAULT_ACTIVITY_CONFIG) {
  return {
    brand: cleanText(input.brand, fallback.brand, 20),
    displayKicker: cleanText(input.displayKicker, fallback.displayKicker, 60),
    displayTitle: cleanText(input.displayTitle, fallback.displayTitle, 40),
    idleTitle: cleanText(input.idleTitle, fallback.idleTitle, 40),
    idleSubtitle: cleanText(input.idleSubtitle, fallback.idleSubtitle, 60),
    mobileTitle: cleanText(input.mobileTitle, fallback.mobileTitle, 30),
    mobileSubtitle: cleanText(input.mobileSubtitle, fallback.mobileSubtitle, 60),
    templates: cleanList(input.templates, fallback.templates, { maxItems: 6, maxLength: 40 }),
    submissionsEnabled: input.submissionsEnabled === undefined
      ? fallback.submissionsEnabled
      : Boolean(input.submissionsEnabled),
    maxWishLength: clampInteger(input.maxWishLength, fallback.maxWishLength, 1, 80),
    maxNameLength: clampInteger(input.maxNameLength, fallback.maxNameLength, 1, 20),
    blockedWords: cleanList(input.blockedWords, fallback.blockedWords, { maxItems: 100, maxLength: 20, allowEmpty: true }),
  };
}

export function activityConfigFromRow(row) {
  if (!row) return normalizeActivityConfig();
  return normalizeActivityConfig({
    brand: row.brand,
    displayKicker: row.display_kicker,
    displayTitle: row.display_title,
    idleTitle: row.idle_title,
    idleSubtitle: row.idle_subtitle,
    mobileTitle: row.mobile_title,
    mobileSubtitle: row.mobile_subtitle,
    templates: parseList(row.templates_json, DEFAULT_ACTIVITY_CONFIG.templates),
    submissionsEnabled: Boolean(row.submissions_enabled),
    maxWishLength: row.max_wish_length,
    maxNameLength: row.max_name_length,
    blockedWords: parseList(row.blocked_words_json, DEFAULT_ACTIVITY_CONFIG.blockedWords),
  });
}

export function activityConfigToRow(room, config, updatedAt = Date.now()) {
  const normalized = normalizeActivityConfig(config);
  return {
    room,
    brand: normalized.brand,
    displayKicker: normalized.displayKicker,
    displayTitle: normalized.displayTitle,
    idleTitle: normalized.idleTitle,
    idleSubtitle: normalized.idleSubtitle,
    mobileTitle: normalized.mobileTitle,
    mobileSubtitle: normalized.mobileSubtitle,
    templatesJson: JSON.stringify(normalized.templates),
    submissionsEnabled: normalized.submissionsEnabled ? 1 : 0,
    maxWishLength: normalized.maxWishLength,
    maxNameLength: normalized.maxNameLength,
    blockedWordsJson: JSON.stringify(normalized.blockedWords),
    updatedAt,
  };
}
