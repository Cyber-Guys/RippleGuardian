import React from "react";
import type { Box, Size } from "../captures";
import { CAM_MOVE, glide } from "../theme";

/** Centre of the view in page pixels, and zoom (1 = the page width fills the window). */
export type Cam = { x: number; y: number; z: number };
export type Key = { at: number; cam: Cam; dur?: number };

export const MAX_ZOOM = 2.2;

/** The camera that frames box `b` with `pad` room around it. */
export const fit = (
  b: Box,
  page: Size,
  view: Size,
  pad = 0.15,
  maxZ = MAX_ZOOM,
): Cam => {
  const base = view.w / page.w;
  const z = Math.min(
    maxZ,
    view.w / (base * b.w * (1 + pad)),
    view.h / (base * b.h * (1 + pad)),
  );
  return { x: b.x + b.w / 2, y: b.y + b.h / 2, z: Math.max(1, z) };
};

export const whole = (page: Size): Cam => ({ x: page.w / 2, y: 540, z: 1 });

/** Keeps the view inside box `b` (for example a panel, so the sidebar stays out of shot). */
export const within = (c: Cam, b: Box, page: Size, view: Size): Cam => {
  const s = (view.w / page.w) * c.z;
  const hw = view.w / s / 2;
  const hh = view.h / s / 2;
  const x =
    b.w <= 2 * hw
      ? b.x + b.w / 2
      : Math.min(b.x + b.w - hw, Math.max(b.x + hw, c.x));
  const y =
    b.h <= 2 * hh
      ? b.y + b.h / 2
      : Math.min(b.y + b.h - hh, Math.max(b.y + hh, c.y));
  return { x, y, z: c.z };
};

/** Never show anything past the edges of the captured page. */
const clamp = (c: Cam, page: Size, view: Size): Cam => {
  const s = (view.w / page.w) * c.z;
  const hw = view.w / s / 2;
  const hh = view.h / s / 2;
  const x =
    page.w <= 2 * hw ? page.w / 2 : Math.min(page.w - hw, Math.max(hw, c.x));
  const y =
    page.h <= 2 * hh ? page.h / 2 : Math.min(page.h - hh, Math.max(hh, c.y));
  return { x, y, z: c.z };
};

/** Eased moves from key to key; zoom is interpolated in log space so it feels even. Keys are
 * kept inside the page first: a path between two valid cameras stays valid, so the per-frame
 * clamp never kicks in halfway through a move. */
export const camAt = (
  frame: number,
  keys: Key[],
  page: Size,
  view: Size,
): Cam => {
  const inside = keys.map((k) => ({ ...k, cam: clamp(k.cam, page, view) }));
  let cam = inside[0].cam;
  for (const k of inside.slice(1)) {
    const p = glide(frame, k.at, k.dur ?? CAM_MOVE);
    if (p === 0) break;
    cam = {
      x: cam.x + (k.cam.x - cam.x) * p,
      y: cam.y + (k.cam.y - cam.y) * p,
      z: Math.exp(Math.log(cam.z) + (Math.log(k.cam.z) - Math.log(cam.z)) * p),
    };
  }
  return cam;
};

type Props = {
  cam: Cam;
  page: Size;
  view: Size;
  /** Receives the page-to-screen scale, so overlays can keep constant line widths. */
  children: (scale: number) => React.ReactNode;
};

/** Page content (a capture, in CSS pixels of the captured viewport) seen through the camera. */
export const CameraMove: React.FC<Props> = ({ cam, page, view, children }) => {
  const c = clamp(cam, page, view);
  const s = (view.w / page.w) * c.z;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: page.w,
        height: page.h,
        transformOrigin: "0 0",
        transform: `translate(${view.w / 2}px, ${view.h / 2}px) scale(${s}) translate(${-c.x}px, ${-c.y}px)`,
      }}
    >
      {children(s)}
    </div>
  );
};
