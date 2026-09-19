const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

export const QUALITY_TIERS = Object.freeze({
  high: Object.freeze({ particles: 6500, pixelRatio: 1.7, bloom: true, smoke: 18 }),
  medium: Object.freeze({ particles: 4000, pixelRatio: 1.3, bloom: true, smoke: 10 }),
  low: Object.freeze({ particles: 2200, pixelRatio: 1, bloom: false, smoke: 4 }),
});

export function seededRandom(seed = 1) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

export function sampleSphere(count, random = Math.random) {
  const total = Math.max(1, Math.floor(count));
  return Array.from({ length: total }, (_, index) => {
    const y = 1 - (2 * (index + .5)) / total;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = index * GOLDEN_ANGLE + (random() - .5) * .09;
    return { x: Math.cos(theta) * radius, y, z: Math.sin(theta) * radius };
  });
}

export function sampleHeartVolume(count, random = Math.random) {
  const total = Math.max(1, Math.floor(count));
  return Array.from({ length: total }, (_, index) => {
    const angle = (Math.PI * 2 * index) / total + (random() - .5) * .025;
    const sin = Math.sin(angle);
    const x = (16 * sin * sin * sin) / 17;
    const y = (13 * Math.cos(angle)
      - 5 * Math.cos(angle * 2)
      - 2 * Math.cos(angle * 3)
      - Math.cos(angle * 4)) / 17;
    const thickness = .16 + Math.abs(y) * .14;
    const z = (random() - .5) * thickness * 2;
    const innerScale = .78 + random() * .22;
    return { x: x * innerScale, y: y * innerScale, z };
  });
}

export function createQualityController(initialTier = "high") {
  const order = ["low", "medium", "high"];
  let tier = QUALITY_TIERS[initialTier] ? initialTier : "high";
  let lowWindows = 0;
  let criticalWindows = 0;
  let highWindows = 0;

  return {
    get tier() { return tier; },
    get profile() { return QUALITY_TIERS[tier]; },
    observe(fps) {
      lowWindows = fps < 42 ? lowWindows + 1 : 0;
      criticalWindows = fps < 24 ? criticalWindows + 1 : 0;
      highWindows = fps > 56 ? highWindows + 1 : 0;
      let changed = false;
      if (lowWindows >= 2 && tier !== "low") {
        tier = order[order.indexOf(tier) - 1];
        lowWindows = 0;
        highWindows = 0;
        changed = true;
      } else if (highWindows >= 4 && tier !== "high") {
        tier = order[order.indexOf(tier) + 1];
        highWindows = 0;
        lowWindows = 0;
        changed = true;
      }
      return { tier, profile: QUALITY_TIERS[tier], changed, fallback: tier === "low" && criticalWindows >= 3 };
    },
  };
}
