# WebGL 3D Fireworks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Three.js WebGL 3D fireworks renderer with perspective, bloom, smoke, 3D round and heart geometry, adaptive quality, and automatic Canvas fallback.

**Architecture:** Keep `display.js` as the WebSocket and launch scheduler. Add a self-contained WebGL renderer with a `launch/clear/destroy/mode` interface and retain the current Canvas classes as fallback; the scheduler sends each wish to whichever renderer is active. Serve pinned Three.js modules from local `node_modules` so the Docker package has no CDN dependency.

**Tech Stack:** Node.js, Express, Three.js 0.185.1, WebGL2, GLSL shaders, Canvas 2D fallback, Node native test runner.

---

### Task 1: Pure 3D geometry and adaptive quality

**Files:**
- Create: `public/fireworks-3d-geometry.js`
- Test: `test/fireworks-3d-geometry.test.mjs`

- [ ] Add tests that assert sphere points occupy both positive and negative Z, heart points have two lobes and a lower tip, and quality moves high → medium → low after sustained low FPS.

```js
const sphere = sampleSphere(256, seededRandom(7));
assert.ok(sphere.some((point) => point.z > 0.5));
assert.ok(sphere.some((point) => point.z < -0.5));
const heart = sampleHeartVolume(360, seededRandom(9));
assert.ok(Math.min(...heart.map((point) => point.y)) < -0.7);
```

- [ ] Run `node --test test/fireworks-3d-geometry.test.mjs` and confirm the missing module fails.

- [ ] Implement deterministic `sampleSphere(count, random)`, `sampleHeartVolume(count, random)`, `createQualityController(initialTier)`, and immutable high/medium/low budgets.

```js
export const QUALITY_TIERS = Object.freeze({
  high: Object.freeze({ particles: 6500, pixelRatio: 1.7, bloom: true, smoke: 18 }),
  medium: Object.freeze({ particles: 4000, pixelRatio: 1.3, bloom: true, smoke: 10 }),
  low: Object.freeze({ particles: 2200, pixelRatio: 1, bloom: false, smoke: 4 }),
});
```

- [ ] Run the focused geometry test and `npm test`; expect all tests to pass.

### Task 2: Bundle and serve Three.js locally

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `server.mjs`
- Modify: `public/display.html`
- Modify: `public/display.css`
- Modify: `test/server.test.mjs`

- [ ] Install `three@0.185.1` and add a server test that fetches `/vendor/three/build/three.module.js` and expects HTTP 200 with JavaScript content.

- [ ] Expose the installed package read-only:

```js
app.use("/vendor/three", express.static(path.join(rootDir, "node_modules", "three"), {
  fallthrough: false,
  immutable: true,
  maxAge: "1y",
}));
```

- [ ] Add an import map for `three` and `three/addons/`, plus `<canvas id="fireworks3d">`; place both canvases in the same fixed stage and toggle visibility with the `hidden` attribute.

- [ ] Run `npm test` and verify the vendor module endpoint passes.

### Task 3: Implement the WebGL particle renderer

**Files:**
- Create: `public/fireworks-webgl.js`

- [ ] Create `createWebGLFireworksRenderer({ canvas, onFallback, onLabel })` using `WebGLRenderer`, `PerspectiveCamera`, `Scene`, `EffectComposer`, `RenderPass`, and `UnrealBloomPass`.

- [ ] Implement a soft circular particle shader with additive blending. Each burst owns typed arrays for position, velocity, color, size, remaining life, and flicker phase and updates `BufferAttribute.needsUpdate` once per frame.

- [ ] Implement rocket ascent, perspective launch positions, procedural smoke `CanvasTexture` sprites, and three style factories:

```js
const styleFactories = {
  velvet: createVelvetBurst,
  jewel: createJewelBurst,
  willow: createWillowBurst,
};
```

- [ ] Use `sampleSphere` for round wishes and rotated `sampleHeartVolume` for heart wishes. Apply style-specific shells, gravity, secondary bursts, duration, bloom strength, and smoke count.

- [ ] Listen for `webglcontextlost`, prevent the browser default restore loop, and invoke `onFallback("context-lost")` exactly once.

### Task 4: Route wishes and preserve Canvas fallback

**Files:**
- Modify: `public/display.js`

- [ ] Parse `renderer=auto|webgl|canvas`; initialize WebGL dynamically unless Canvas is forced.

- [ ] Add `launchWish(wish, ambient)` so queue, ambient, and replay paths use one function:

```js
function launchWish(wish, ambient = false) {
  if (webglRenderer) webglRenderer.launch(wish, { ambient });
  else active.push(new Firework(wish, ambient));
}
```

- [ ] On WebGL initialization failure or renderer fallback, hide the 3D canvas, show the Canvas canvas, set `document.body.dataset.renderer = "canvas"`, and continue consuming the existing queue.

- [ ] Route `history-cleared` to both the pending queue and `webglRenderer.clear()`; leave the DOM wish labels and history wall unchanged.

- [ ] Add the runtime quality callback: update `data-quality`, progressively reduce composer pixel ratio and effects, and fall back only after the low tier remains below 24 FPS.

### Task 5: Version, browser QA, and sustained verification

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `docker-compose.yml`
- Modify: `server.mjs`
- Modify: `DEPLOY.md`

- [ ] Bump all application version references to `0.2.0` to mark the renderer architecture change.

- [ ] Run syntax checks, `npm test`, `docker compose config --quiet`, and verify `/vendor/three/build/three.module.js` from the running service.

- [ ] Restart port 18894 with current LAN IP and the existing preview database.

- [ ] Verify `renderer=webgl` sets `data-renderer="webgl"`, `renderer=canvas` sets Canvas mode, and forced WebGL reports no console errors on the target browser.

- [ ] Submit all six shape/style combinations, visually inspect 3D depth and heart recognition, then run a 10-minute frame monitor; record average/minimum FPS and final quality tier.
