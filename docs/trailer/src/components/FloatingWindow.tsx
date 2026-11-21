import React from "react";
import { C } from "../theme";

/** Default window: 75% of the frame, room for the caption underneath. */
export const VIEW = { w: 1440, h: 810 };
export const TITLE_BAR = 34;
export const WIN = { x: (1920 - VIEW.w) / 2, y: 40 };

type Props = {
  children: React.ReactNode;
  x?: number;
  y?: number;
  width?: number;
  enter?: number; // 0..1, rise and fade in
  opacity?: number;
  scale?: number;
};

/** Rounded, chrome-less browser frame with a soft shadow, floating on the stage. */
export const FloatingWindow: React.FC<Props> = ({
  children,
  x = WIN.x,
  y = WIN.y,
  width = VIEW.w,
  enter = 1,
  opacity = 1,
  scale = 1,
}) => {
  const height = (width * 9) / 16;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height: height + TITLE_BAR,
        borderRadius: 18,
        overflow: "hidden",
        background: C.mist,
        opacity: enter * opacity,
        transform: `translateY(${(1 - enter) * 24}px) scale(${(0.97 + 0.03 * enter) * scale})`,
        transformOrigin: "50% 60%",
        boxShadow:
          "0 40px 90px rgba(0, 0, 0, 0.55), 0 12px 30px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(225, 232, 239, 0.14)",
      }}
    >
      <div
        style={{
          height: TITLE_BAR,
          display: "flex",
          alignItems: "center",
          gap: 8,
          paddingLeft: 16,
          borderBottom: "1px solid rgba(11, 18, 32, 0.08)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 12,
              height: 12,
              borderRadius: 6,
              background: "rgba(11, 18, 32, 0.2)",
            }}
          />
        ))}
      </div>
      <div style={{ position: "relative", width, height, overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
};
