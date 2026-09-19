import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

import {
  createQualityController,
  sampleHeartVolume,
  sampleSphere,
} from "./fireworks-3d-geometry.js";

const PALETTES = {
  gold: ["#fff3bd", "#ffd467", "#ff9748"],
  rose: ["#ffe5ee", "#ff79a5", "#ff3f78"],
  cyan: ["#e5fcff", "#58eaff", "#338dff"],
  violet: ["#f5ecff", "#b697ff", "#7448ff"],
  emerald: ["#dcfff2", "#5cf0bb", "#16b982"],
};

const STYLE = {
  velvet: { duration: 5, speed: 2.15, gravity: .32, drag: .985, bloom: .58, scale: 2.35 },
  jewel: { duration: 4.5, speed: 2.8, gravity: .22, drag: .978, bloom: .86, scale: 2.55 },
  willow: { duration: 6, speed: 2.05, gravity: .58, drag: .992, bloom: .68, scale: 2.8 },
};

const vertexShader = `
  attribute float aSize;
  attribute float aAlpha;
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vColor = color;
    vAlpha = aAlpha;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize * (22.0 / max(1.0, -mvPosition.z));
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec2 centered = gl_PointCoord - vec2(0.5);
    float distanceToCenter = length(centered);
    if (distanceToCenter > 0.5) discard;
    float core = smoothstep(0.5, 0.02, distanceToCenter);
    float halo = smoothstep(0.5, 0.12, distanceToCenter);
    vec3 color = vColor * (1.0 + core * 1.8);
    gl_FragColor = vec4(color, vAlpha * (halo * 0.65 + core * 0.55));
  }
`;

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

function createSmokeTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(64, 64, 4, 64, 64, 62);
  gradient.addColorStop(0, "rgba(255,255,255,.42)");
  gradient.addColorStop(.3, "rgba(180,205,255,.16)");
  gradient.addColorStop(1, "rgba(25,38,75,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 128, 128);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function createParticleMaterial() {
  return new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    transparent: true,
    depthWrite: false,
    vertexColors: true,
    blending: THREE.AdditiveBlending,
  });
}

function paletteFor(wish) {
  const base = PALETTES[wish?.color] || PALETTES.gold;
  if (wish?.style === "jewel") return [...base, "#ffffff", "#63efff", "#ff70bc"];
  if (wish?.style === "willow") return [...base, "#ffd873", "#ff8e46", "#ff5546"];
  return [...base, "#fff8d4", "#ffc35a"];
}

function createParticleSystem({ wish, center, quality, shape }) {
  const styleName = STYLE[wish?.style] ? wish.style : "velvet";
  const style = STYLE[styleName];
  const shapeName = shape || (wish?.shape === "heart" ? "heart" : "burst");
  const fraction = styleName === "willow" ? .055 : styleName === "jewel" ? .045 : .05;
  const count = Math.max(180, Math.floor(quality.particles * fraction));
  const points = shapeName === "heart" ? sampleHeartVolume(count) : sampleSphere(count);
  const positions = new Float32Array(count * 3);
  const velocities = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const alphas = new Float32Array(count);
  const remaining = new Float32Array(count);
  const phases = new Float32Array(count);
  const palette = paletteFor(wish).map((color) => new THREE.Color(color));
  const heartRotation = shapeName === "heart" ? randomBetween(-.22, .22) : 0;
  const cosRotation = Math.cos(heartRotation);
  const sinRotation = Math.sin(heartRotation);

  for (let index = 0; index < count; index += 1) {
    const point = points[index];
    let dx = point.x;
    let dy = point.y;
    let dz = point.z;
    if (shapeName === "heart") {
      const rotatedX = dx * cosRotation - dz * sinRotation;
      dz = dx * sinRotation + dz * cosRotation;
      dx = rotatedX;
    }
    if (styleName === "willow" && shapeName === "burst") dy = Math.abs(dy) * .9 - .05;
    const length = Math.hypot(dx, dy, dz) || 1;
    const shell = styleName === "velvet" && index % 3 ? .72 : 1;
    const ray = styleName === "jewel" && index % 7 === 0 ? 1.45 : 1;
    const speed = style.speed * shell * ray * randomBetween(.82, 1.18);
    const offset = index * 3;
    positions[offset] = center.x;
    positions[offset + 1] = center.y;
    positions[offset + 2] = center.z;
    velocities[offset] = (dx / length) * speed * style.scale;
    velocities[offset + 1] = (dy / length) * speed * style.scale;
    velocities[offset + 2] = (dz / length) * speed * style.scale;
    const color = palette[index % palette.length];
    colors[offset] = color.r;
    colors[offset + 1] = color.g;
    colors[offset + 2] = color.b;
    sizes[index] = randomBetween(styleName === "jewel" ? 3.2 : 2.4, styleName === "willow" ? 5.8 : 4.8);
    alphas[index] = 1;
    remaining[index] = style.duration * randomBetween(.82, 1.04);
    phases[index] = Math.random() * Math.PI * 2;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geometry.setAttribute("aAlpha", new THREE.BufferAttribute(alphas, 1));
  const material = createParticleMaterial();
  const object = new THREE.Points(geometry, material);
  object.frustumCulled = false;

  return {
    object,
    center: center.clone(),
    styleName,
    positions,
    velocities,
    alphas,
    remaining,
    phases,
    duration: style.duration,
    drag: style.drag,
    gravity: style.gravity,
    age: 0,
    secondaryTriggered: false,
    update(delta) {
      this.age += delta;
      let alive = 0;
      const frameDrag = Math.pow(this.drag, delta * 60);
      for (let index = 0; index < count; index += 1) {
        if (this.remaining[index] <= 0) {
          this.alphas[index] = 0;
          continue;
        }
        alive += 1;
        this.remaining[index] -= delta;
        const offset = index * 3;
        this.velocities[offset] *= frameDrag;
        this.velocities[offset + 1] = this.velocities[offset + 1] * frameDrag - this.gravity * delta;
        this.velocities[offset + 2] *= frameDrag;
        this.positions[offset] += this.velocities[offset] * delta;
        this.positions[offset + 1] += this.velocities[offset + 1] * delta;
        this.positions[offset + 2] += this.velocities[offset + 2] * delta;
        const progress = Math.max(0, this.remaining[index] / this.duration);
        const flicker = styleName === "jewel" ? .68 + Math.sin(this.phases[index] + this.age * 12) * .32 : 1;
        const fadeIn = Math.min(1, this.age / .24);
        this.alphas[index] = Math.pow(progress, .68) * flicker * fadeIn * .68;
      }
      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.aAlpha.needsUpdate = true;
      return alive > 0;
    },
    dispose() {
      geometry.dispose();
      material.dispose();
    },
  };
}

export function createWebGLFireworksRenderer({ canvas, onFallback, onLabel, onQuality, onMetrics }) {
  if (!canvas || !window.WebGL2RenderingContext) throw new Error("WebGL2 unavailable");

  let fallbackSent = false;
  const fail = (reason) => {
    if (fallbackSent) return;
    fallbackSent = true;
    onFallback?.(reason);
  };

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: false, antialias: true, powerPreference: "high-performance" });
  renderer.setClearColor(0x000000, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .9;
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x071127, .022);
  const camera = new THREE.PerspectiveCamera(46, 1, .1, 80);
  camera.position.set(0, .5, 15);
  const composer = new EffectComposer(renderer);
  const renderPass = new RenderPass(scene, camera);
  const bloomPass = new UnrealBloomPass(new THREE.Vector2(1, 1), 1.35, .62, .06);
  composer.addPass(renderPass);
  composer.addPass(bloomPass);
  const smokeTexture = createSmokeTexture();
  const qualityController = createQualityController("high");
  const rockets = [];
  const systems = [];
  const smokes = [];
  let animationFrame = 0;
  let disposed = false;
  let frameCount = 0;
  let frameWindowStarted = performance.now();
  let mouseX = 0;
  let mouseY = 0;
  let lastFrameTime = performance.now();

  function applyQuality(profile, tier) {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, profile.pixelRatio));
    bloomPass.enabled = profile.bloom;
    onQuality?.(tier, profile);
    resize();
  }

  function resize() {
    const width = Math.max(1, window.innerWidth);
    const height = Math.max(1, window.innerHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    composer.setSize(width, height);
  }

  function spawnSmoke(position, count) {
    const smokeCount = Math.min(count, qualityController.profile.smoke);
    for (let index = 0; index < smokeCount; index += 1) {
      const material = new THREE.SpriteMaterial({
        map: smokeTexture,
        color: index % 3 === 0 ? 0xd6ddff : 0x8190b0,
        transparent: true,
        opacity: randomBetween(.08, .18),
        depthWrite: false,
        blending: THREE.NormalBlending,
      });
      const sprite = new THREE.Sprite(material);
      sprite.position.copy(position).add(new THREE.Vector3(randomBetween(-.35, .35), randomBetween(-.2, .3), randomBetween(-.3, .3)));
      const scale = randomBetween(.55, 1.25);
      sprite.scale.set(scale, scale, 1);
      scene.add(sprite);
      smokes.push({ sprite, material, life: randomBetween(2.2, 3.8), maxLife: 3.8, drift: randomBetween(-.08, .12) });
    }
  }

  function explode(rocket) {
    const system = createParticleSystem({
      wish: rocket.wish,
      center: rocket.target,
      quality: qualityController.profile,
    });
    systems.push(system);
    scene.add(system.object);
    bloomPass.strength = STYLE[system.styleName].bloom;
    spawnSmoke(rocket.target, rocket.wish?.style === "willow" ? 18 : 10);
    const projected = rocket.target.clone().project(camera);
    if (!rocket.ambient && rocket.wish) {
      onLabel?.(
        rocket.wish,
        (projected.x * .5 + .5) * window.innerWidth,
        (-projected.y * .5 + .5) * window.innerHeight,
      );
    }
  }

  function launch(wish, { ambient = false } = {}) {
    const start = new THREE.Vector3(randomBetween(-3.4, 3.4), -6.2, randomBetween(-1.2, 1.2));
    const target = new THREE.Vector3(randomBetween(-3.4, 3.4), randomBetween(.2, 4.2), randomBetween(-2.2, 2.2));
    const material = new THREE.SpriteMaterial({ color: new THREE.Color((PALETTES[wish?.color] || PALETTES.gold)[0]), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(.18, .18, 1);
    sprite.position.copy(start);
    scene.add(sprite);
    rockets.push({ wish, ambient, start, target, sprite, material, age: 0, duration: randomBetween(.62, .86), smokeClock: 0 });
  }

  function clear() {
    for (const rocket of rockets.splice(0)) {
      scene.remove(rocket.sprite);
      rocket.material.dispose();
    }
    for (const system of systems.splice(0)) {
      scene.remove(system.object);
      system.dispose();
    }
    for (const smoke of smokes.splice(0)) {
      scene.remove(smoke.sprite);
      smoke.material.dispose();
    }
  }

  function updateRockets(delta) {
    for (let index = rockets.length - 1; index >= 0; index -= 1) {
      const rocket = rockets[index];
      rocket.age += delta;
      rocket.smokeClock += delta;
      const progress = Math.min(1, rocket.age / rocket.duration);
      const eased = 1 - Math.pow(1 - progress, 2.6);
      rocket.sprite.position.lerpVectors(rocket.start, rocket.target, eased);
      rocket.sprite.material.opacity = .75 + Math.sin(progress * Math.PI * 9) * .25;
      if (rocket.smokeClock > .09) {
        spawnSmoke(rocket.sprite.position, 1);
        rocket.smokeClock = 0;
      }
      if (progress >= 1) {
        scene.remove(rocket.sprite);
        rocket.material.dispose();
        rockets.splice(index, 1);
        explode(rocket);
      }
    }
  }

  function updateSystems(delta) {
    for (let index = systems.length - 1; index >= 0; index -= 1) {
      const system = systems[index];
      if (system.styleName === "jewel" && !system.secondaryTriggered && system.age > .58 && systems.length < 6) {
        system.secondaryTriggered = true;
        const offset = new THREE.Vector3(randomBetween(-.8, .8), randomBetween(-.4, .8), randomBetween(-.7, .7));
        const secondaryWish = { color: "cyan", style: "jewel", shape: "burst" };
        const secondary = createParticleSystem({ wish: secondaryWish, center: system.center.clone().add(offset), quality: { ...qualityController.profile, particles: Math.floor(qualityController.profile.particles * .28) } });
        systems.push(secondary);
        scene.add(secondary.object);
      }
      if (!system.update(delta)) {
        scene.remove(system.object);
        system.dispose();
        systems.splice(index, 1);
      }
    }
  }

  function updateSmoke(delta) {
    for (let index = smokes.length - 1; index >= 0; index -= 1) {
      const smoke = smokes[index];
      smoke.life -= delta;
      smoke.sprite.position.x += smoke.drift * delta;
      smoke.sprite.position.y += .08 * delta;
      smoke.sprite.scale.multiplyScalar(1 + delta * .22);
      smoke.material.opacity = Math.max(0, (smoke.life / smoke.maxLife) * .14);
      if (smoke.life <= 0) {
        scene.remove(smoke.sprite);
        smoke.material.dispose();
        smokes.splice(index, 1);
      }
    }
  }

  function animate(timestamp = performance.now()) {
    if (disposed) return;
    animationFrame = requestAnimationFrame(animate);
    const delta = Math.min(Math.max((timestamp - lastFrameTime) / 1000, 0), .05);
    lastFrameTime = timestamp;
    updateRockets(delta);
    updateSystems(delta);
    updateSmoke(delta);
    camera.position.x += (mouseX * .32 - camera.position.x) * .014;
    camera.position.y += ((.5 + mouseY * .18) - camera.position.y) * .014;
    camera.lookAt(0, .2, 0);
    composer.render();
    frameCount += 1;
    const now = performance.now();
    if (now - frameWindowStarted >= 3000) {
      const fps = (frameCount * 1000) / (now - frameWindowStarted);
      const result = qualityController.observe(fps);
      onMetrics?.({ fps: Math.round(fps), tier: result.tier });
      if (result.changed) applyQuality(result.profile, result.tier);
      if (result.fallback) fail("low-fps");
      frameCount = 0;
      frameWindowStarted = now;
    }
  }

  function onPointerMove(event) {
    mouseX = (event.clientX / Math.max(1, window.innerWidth) - .5) * 2;
    mouseY = -((event.clientY / Math.max(1, window.innerHeight) - .5) * 2);
  }

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    fail("context-lost");
  });
  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", onPointerMove, { passive: true });
  applyQuality(qualityController.profile, qualityController.tier);
  animate();

  return {
    mode: "webgl",
    launch,
    clear,
    resize,
    get quality() { return qualityController.tier; },
    destroy() {
      if (disposed) return;
      disposed = true;
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      clear();
      smokeTexture.dispose();
      composer.dispose();
      renderer.dispose();
    },
  };
}
