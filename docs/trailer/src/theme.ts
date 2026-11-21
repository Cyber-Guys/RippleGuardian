import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { Easing, interpolate } from "remotion";

export const INTER = loadInter("normal", {
  weights: ["400", "500", "600"],
  subsets: ["latin"],
}).fontFamily;
export const MONO = loadMono("normal", {
  weights: ["400", "500"],
  subsets: ["latin"],
}).fontFamily;

// The whole palette of the film.
export const C = {
  stage: "#0b1220",
  white: "#ffffff",
  mist: "#e1e8ef",
  danger: "#b4233a",
  glow: "#a3192f",
  blue: "#5ea2f5",
  blue2: "#4a9be0",
} as const;

export const EASE = Easing.bezier(0.16, 1, 0.3, 1); // captions and UI, from the brief
export const MOVE = 36; // frames per UI move (600 ms)

// The camera starts and lands at zero speed, so pushes and pans never jerk.
export const CAM_EASE = Easing.bezier(0.42, 0, 0.2, 1);
export const CAM_MOVE = 72; // frames per camera move (1.2 s)

/** 0 until `start`, then eased to 1 over `dur` frames. */
export const ramp = (frame: number, start: number, dur = MOVE): number =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: EASE,
  });

/** Like `ramp`, with the camera's ease-in-out. */
export const glide = (frame: number, start: number, dur = CAM_MOVE): number =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: CAM_EASE,
  });

/** Visible between `start` and `end`, with short fades on both sides. */
export const during = (
  frame: number,
  start: number,
  end: number,
  fade = 12,
): number =>
  Math.min(ramp(frame, start, fade), 1 - ramp(frame, end - fade, fade));
