// Real screens of the running app, saved by capture.py (git-ignored, see README).
import manifest from "../public/captures/manifest.json";

export type Box = { x: number; y: number; w: number; h: number };
export type Size = { w: number; h: number };
type Capture = {
  file: string;
  size: { width: number; height: number };
  boxes: Record<string, Box>;
  marks?: Record<string, number>;
};

const all = manifest.captures as unknown as Capture[];
export const values = manifest.values;

const capture = (file: string): Capture => {
  const c = all.find((x) => x.file === file);
  if (!c) throw new Error(`manifest.json: no capture ${file}`);
  return c;
};

export const box = (file: string, key: string): Box => {
  const b = capture(file).boxes[key];
  if (!b) throw new Error(`manifest.json: ${file} has no box "${key}"`);
  return b;
};

export const pageOf = (file: string): Size => {
  const s = capture(file).size;
  return { w: s.width, h: s.height };
};

/** Seconds into a recording at which capture.py logged `key`. */
export const mark = (file: string, key: string): number => {
  const m = capture(file).marks?.[key];
  if (m === undefined)
    throw new Error(`manifest.json: ${file} has no mark "${key}"`);
  return m;
};

export const union = (...bs: Box[]): Box => {
  const x = Math.min(...bs.map((b) => b.x));
  const y = Math.min(...bs.map((b) => b.y));
  const r = Math.max(...bs.map((b) => b.x + b.w));
  const bottom = Math.max(...bs.map((b) => b.y + b.h));
  return { x, y, w: r - x, h: bottom - y };
};

export const grow = (b: Box, dx: number, dy = dx): Box => ({
  x: b.x - dx,
  y: b.y - dy,
  w: b.w + 2 * dx,
  h: b.h + 2 * dy,
});

export const lerpBox = (a: Box, b: Box, t: number): Box => ({
  x: a.x + (b.x - a.x) * t,
  y: a.y + (b.y - a.y) * t,
  w: a.w + (b.w - a.w) * t,
  h: a.h + (b.h - a.h) * t,
});

/** All graph nodes of one hop column of the trace, as one box. */
export const hopBox = (file: string, hop: number): Box =>
  union(
    ...values.trace.nodes
      .filter((n) => n.hop === hop)
      .map((n) => box(file, n.id)),
  );

export const src = (file: string) => `captures/${file}`;
