const STYLE_PROFILES = Object.freeze({
  velvet: Object.freeze({ particleLife: 300, drag: 0.988, gravity: 0.022, trailAlpha: 0.82 }),
  jewel: Object.freeze({ particleLife: 270, drag: 0.982, gravity: 0.018, trailAlpha: 0.94 }),
  willow: Object.freeze({ particleLife: 360, drag: 0.992, gravity: 0.038, trailAlpha: 0.88 }),
});

export function fireworkStyleProfile(style) {
  return STYLE_PROFILES[style] || STYLE_PROFILES.velvet;
}

export function radialVelocity(angle, speed, downwardBias = 0) {
  return {
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed + downwardBias,
  };
}

export function heartVelocity(angle, scale) {
  const sin = Math.sin(angle);
  const x = 16 * sin * sin * sin;
  const y = 13 * Math.cos(angle)
    - 5 * Math.cos(angle * 2)
    - 2 * Math.cos(angle * 3)
    - Math.cos(angle * 4);
  return {
    vx: x * scale,
    vy: -y * scale,
  };
}
