# Selectable Firework Styles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three independently selectable firework styles that combine with round and heart shapes, persist through live messages and history, and remain visible for 4.5–6 seconds.

**Architecture:** Extend wish normalization and SQLite persistence with a validated `style` value. Keep rendering parameters and pure geometry helpers in `public/firework-geometry.js`, while `public/display.js` maps each style to distinct particle layers, physics, glow, and lifespan. The mobile page remains a two-stage single-select form and submits both `shape` and `style`.

**Tech Stack:** Node.js, Express, SQLite (`better-sqlite3`), WebSocket, browser Canvas 2D, native Node test runner.

---

### Task 1: Persist and transmit a validated style

**Files:**
- Modify: `lib/core.mjs`
- Modify: `server.mjs`
- Modify: `test/core.test.mjs`
- Modify: `test/server.test.mjs`

- [ ] **Step 1: Add failing normalization and transport assertions**

Add assertions that `velvet`, `jewel`, and `willow` are accepted, an unknown style falls back to `velvet`, and the server returns `style: "willow"` in accepted, broadcast, and history payloads.

```js
assert.equal(normalizeWish({ text: "祝福", style: "willow" }).value.style, "willow");
assert.equal(normalizeWish({ text: "祝福", style: "unknown" }).value.style, "velvet");
assert.equal(accepted.wish.style, "willow");
assert.equal(wishBroadcast.wish.style, "willow");
assert.equal(historyAfterSubmit.history[0].style, "willow");
```

- [ ] **Step 2: Run tests and confirm the missing field fails**

Run: `npm test`

Expected: normalization or server assertions fail because `style` is absent.

- [ ] **Step 3: Implement validation and database migration**

Add a style set and normalized fallback:

```js
export const FIREWORK_STYLES = new Set(["velvet", "jewel", "willow"]);
const style = FIREWORK_STYLES.has(input?.style) ? input.style : "velvet";
```

Add `style TEXT NOT NULL DEFAULT 'velvet'` to new schemas, automatically `ALTER TABLE` old databases when the column is absent, then include `style` in insert and history queries.

- [ ] **Step 4: Run tests and confirm persistence passes**

Run: `npm test`

Expected: all core and server tests pass, including legacy-schema migration.

### Task 2: Define pure style timing and geometry helpers

**Files:**
- Modify: `public/firework-geometry.js`
- Modify: `test/firework-geometry.test.mjs`

- [ ] **Step 1: Add failing style-profile tests**

Test exact style lifetimes and fallback behavior:

```js
assert.equal(fireworkStyleProfile("velvet").particleLife, 300);
assert.equal(fireworkStyleProfile("jewel").particleLife, 270);
assert.equal(fireworkStyleProfile("willow").particleLife, 360);
assert.deepEqual(fireworkStyleProfile("unknown"), fireworkStyleProfile("velvet"));
```

Also test that `radialVelocity()` returns the expected direction and that willow downward bias is positive.

- [ ] **Step 2: Run the geometry test and verify it fails**

Run: `node --test test/firework-geometry.test.mjs`

Expected: fail because `fireworkStyleProfile` and `radialVelocity` are not exported.

- [ ] **Step 3: Implement immutable style profiles and radial helper**

```js
const STYLE_PROFILES = Object.freeze({
  velvet: Object.freeze({ particleLife: 300, drag: 0.988, gravity: 0.022, trailAlpha: 0.82 }),
  jewel: Object.freeze({ particleLife: 270, drag: 0.982, gravity: 0.018, trailAlpha: 0.94 }),
  willow: Object.freeze({ particleLife: 360, drag: 0.992, gravity: 0.038, trailAlpha: 0.88 }),
});

export function fireworkStyleProfile(style) {
  return STYLE_PROFILES[style] || STYLE_PROFILES.velvet;
}

export function radialVelocity(angle, speed, downwardBias = 0) {
  return { vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed + downwardBias };
}
```

- [ ] **Step 4: Run the geometry tests**

Run: `node --test test/firework-geometry.test.mjs`

Expected: all geometry tests pass.

### Task 3: Add a compact mobile style selector

**Files:**
- Modify: `public/join.html`
- Modify: `public/join.css`
- Modify: `public/join.js`

- [ ] **Step 1: Add three semantic single-select buttons**

Add a fieldset after the shape selector with buttons carrying `data-style="velvet"`, `data-style="jewel"`, and `data-style="willow"`. Set only velvet to `aria-pressed="true"` initially.

```html
<button class="style-option selected" data-style="velvet" type="button" aria-pressed="true">
  <span class="style-swatch velvet-swatch"></span><span><b>丝绒金雨</b><small>细密柔和</small></span>
</button>
```

- [ ] **Step 2: Implement selection and submission state**

```js
const styleOptions = document.querySelectorAll(".style-option");
let selectedStyle = "velvet";

styleOptions.forEach((button) => {
  button.addEventListener("click", () => {
    styleOptions.forEach((item) => {
      const selected = item === button;
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    selectedStyle = button.dataset.style;
  });
});
```

Include `style: selectedStyle` in the submit payload.

- [ ] **Step 3: Style a responsive three-card row**

Use a three-column grid on normal phones, concise labels, distinct gold/cyan-pink/red-gold swatches, and a two-column fallback below 360 CSS pixels. Keep the launcher visible without horizontal overflow.

- [ ] **Step 4: Run syntax checks**

Run: `node --check public/join.js`

Expected: exit 0.

### Task 4: Render six visibly different combinations

**Files:**
- Modify: `public/display.js`

- [ ] **Step 1: Apply style profiles to each firework and particle**

Import `fireworkStyleProfile` and `radialVelocity`, store `this.style` and `this.profile`, and pass per-particle drag, gravity, fade curve, and trail length into `Particle`.

- [ ] **Step 2: Implement three round explosion methods**

Implement layered methods with bounded particle counts:

```js
explodeVelvetBurst()  // two radial shells, fine gold rain, soft secondary glitter
explodeJewelBurst()   // crisp alternating rays, white core flash, short star points
explodeWillowBurst()  // broad gold-red crown, long downward trails, ember droplets
```

- [ ] **Step 3: Implement three heart treatments**

Use the existing `heartVelocity()` outline as the shared boundary, then vary layers: double outline and interior glitter for velvet, neon outline and short rays for jewel, and gold-red outline plus falling tails for willow.

- [ ] **Step 4: Extend label and particle lifetime without slowing launch**

Keep `ASCENT_FRAMES` and `LAUNCH_INTERVAL_MS` unchanged. Make particle life style-specific and keep labels visible for 7 seconds. Raise the bounded particle cap only as needed for three simultaneous effects.

- [ ] **Step 5: Run syntax and unit tests**

Run: `node --check public/display.js && npm test`

Expected: syntax succeeds and all tests pass.

### Task 5: Version, live verification, and local handoff

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `docker-compose.yml`
- Modify: `server.mjs`
- Modify: `DEPLOY.md`

- [ ] **Step 1: Bump the application version to 0.1.6**

Update all runtime, package, compose image, and deployment-document references from `0.1.5` to `0.1.6`.

- [ ] **Step 2: Run full verification**

Run:

```bash
node --check public/join.js
node --check public/display.js
node --check server.mjs
npm test
docker compose config --quiet
```

Expected: all syntax checks exit 0, all tests pass, and Compose configuration is valid.

- [ ] **Step 3: Restart the local preview with the existing database**

Start with `PORT=18894`, `PUBLIC_BASE_URL=http://192.168.1.105:18894`, `APP_VERSION=0.1.6`, the preview admin token, and the existing preview SQLite path.

- [ ] **Step 4: Exercise all six combinations**

Submit each `shape` and `style` combination through WebSocket, confirm accepted and display broadcasts match the request, then verify history preserves both fields.

- [ ] **Step 5: Perform browser QA**

At a 390×844 viewport, verify both selector groups have exactly one pressed button, all three styles can be selected, and the page has no horizontal overflow. On the display, visually confirm the three styles differ and their particles remain visible for the specified durations.
