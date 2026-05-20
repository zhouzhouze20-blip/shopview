type Point = {
  x: number;
  y: number;
};

let measureSvg: SVGSVGElement | null = null;

function ensureMeasureSvg() {
  if (typeof document === "undefined") return null;
  if (measureSvg?.isConnected) return measureSvg;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.setAttribute("aria-hidden", "true");
  svg.style.position = "absolute";
  svg.style.width = "0";
  svg.style.height = "0";
  svg.style.overflow = "hidden";
  svg.style.pointerEvents = "none";
  svg.style.opacity = "0";
  svg.style.left = "-99999px";
  svg.style.top = "-99999px";
  document.body.appendChild(svg);
  measureSvg = svg;
  return svg;
}

function getAnchorFromPathStart(d: string): Point | null {
  const nums = d.match(/[-+]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][-+]?\d+)?/g);
  if (!nums || nums.length < 2) return null;
  const x = Number(nums[0]);
  const y = Number(nums[1]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x, y };
}

export function getPathVisualCenter(d: string): Point | null {
  const svg = ensureMeasureSvg();
  if (!svg) return getAnchorFromPathStart(d);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  svg.appendChild(path);

  try {
    const bbox = path.getBBox();
    if (Number.isFinite(bbox.x) && Number.isFinite(bbox.y) && bbox.width >= 0 && bbox.height >= 0) {
      return {
        x: bbox.x + bbox.width / 2,
        y: bbox.y + bbox.height / 2,
      };
    }
  } catch {
    return getAnchorFromPathStart(d);
  } finally {
    svg.removeChild(path);
  }

  return getAnchorFromPathStart(d);
}
