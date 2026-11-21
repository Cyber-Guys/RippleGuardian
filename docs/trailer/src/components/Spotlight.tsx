import React from "react";
import type { Box } from "../captures";
import { C } from "../theme";

type Props = {
  box: Box; // page pixels, drawn inside CameraMove
  scale: number; // page-to-screen scale from CameraMove
  opacity: number;
  color?: string;
  dim?: boolean; // false: ring only
  pad?: number; // screen pixels
  pulse?: number; // 0..1, widens the glow
};

/** Dims everything outside `box` and draws a soft ring around it. */
export const Spotlight: React.FC<Props> = ({
  box,
  scale,
  opacity,
  color = C.blue,
  dim = true,
  pad = 12,
  pulse = 0,
}) => {
  if (opacity <= 0) return null;
  const p = pad / scale;
  const glow = `0 0 ${(16 + 26 * pulse) / scale}px ${(2 + 4 * pulse) / scale}px ${color}`;
  return (
    <div
      style={{
        position: "absolute",
        left: box.x - p,
        top: box.y - p,
        width: box.w + 2 * p,
        height: box.h + 2 * p,
        borderRadius: 16 / scale,
        border: `${3 / scale}px solid ${color}`,
        opacity,
        boxShadow: dim
          ? `${glow}, 0 0 0 ${6000 / scale}px rgba(11, 18, 32, 0.62)`
          : glow,
      }}
    />
  );
};
