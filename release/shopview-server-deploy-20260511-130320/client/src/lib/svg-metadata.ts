const SVG_LENGTH_RE = /[-+]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][-+]?\d+)?/;

export type SvgMetadata = {
  viewBox: string | null;
  width: number | null;
  height: number | null;
};

function parseSvgLength(value?: string | null) {
  if (!value) return null;
  const match = value.trim().match(SVG_LENGTH_RE);
  if (!match) return null;
  const num = Number(match[0]);
  return Number.isFinite(num) ? num : null;
}

export function normalizeSvgViewBox(value?: string | null) {
  const raw = value?.trim();
  if (!raw) return null;
  const parts = raw.split(/[\s,]+/).map((item) => Number(item));
  if (parts.length !== 4 || parts.some((item) => !Number.isFinite(item))) return null;
  return parts.join(" ");
}

export function deriveSvgViewBox(meta: Partial<SvgMetadata>) {
  const normalizedViewBox = normalizeSvgViewBox(meta.viewBox);
  if (normalizedViewBox) return normalizedViewBox;

  if (meta.width != null && meta.height != null && meta.width > 0 && meta.height > 0) {
    return `0 0 ${meta.width} ${meta.height}`;
  }

  return null;
}

export function extractSvgMetadataFromText(text: string): SvgMetadata {
  const doc = new DOMParser().parseFromString(text, "image/svg+xml");
  const root = doc.documentElement;
  if (!root || root.nodeName.toLowerCase() !== "svg") {
    return { viewBox: null, width: null, height: null };
  }

  const width = parseSvgLength(root.getAttribute("width"));
  const height = parseSvgLength(root.getAttribute("height"));
  const viewBox = normalizeSvgViewBox(root.getAttribute("viewBox"));

  return { viewBox, width, height };
}
