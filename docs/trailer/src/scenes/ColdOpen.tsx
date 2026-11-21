import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import mark from "../../../../src/ixh26/app/static/logo-mark.png";
import { C, INTER, ramp } from "../theme";
import { at, type SceneProps } from "../timing";

const LINE = "Your seed just leaked.";

/** Scene 1: a lock-screen notification on the chime, then a line types under it. */
export const ColdOpen: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const enter = ramp(frame, at(p, "chime"), 36);
  const typeAt = at(p, "typeLine");
  const typed = Math.max(
    0,
    Math.min(LINE.length, Math.floor((frame - typeAt) / 3)),
  );
  const caret = frame >= typeAt && Math.floor((frame - typeAt) / 15) % 2 === 0;
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        fontFamily: INTER,
      }}
    >
      <div
        style={{
          opacity: enter,
          transform: `translateY(${(enter - 1) * 40}px)`,
          width: 880,
          padding: "30px 34px",
          borderRadius: 34,
          display: "flex",
          alignItems: "center",
          gap: 26,
          background: "rgba(225, 232, 239, 0.08)",
          border: "1px solid rgba(225, 232, 239, 0.14)",
          boxShadow: "0 30px 80px rgba(0, 0, 0, 0.5)",
        }}
      >
        <Img src={mark} style={{ width: 88, height: 88, borderRadius: 20 }} />
        <div>
          <div
            style={{
              color: C.mist,
              opacity: 0.7,
              fontSize: 27,
              fontWeight: 500,
              whiteSpace: "pre",
            }}
          >
            {"3:12 AM  ·  Ripple Guardian"}
          </div>
          <div
            style={{
              color: C.white,
              fontSize: 46,
              fontWeight: 600,
              marginTop: 4,
            }}
          >
            Signing key changed
          </div>
        </div>
      </div>
      <div
        style={{
          marginTop: 64,
          fontSize: 52,
          fontWeight: 500,
          color: C.mist,
          whiteSpace: "pre",
        }}
      >
        <span>{LINE.slice(0, typed)}</span>
        <span style={{ color: C.danger, opacity: caret ? 1 : 0 }}>|</span>
        <span style={{ opacity: 0 }}>{LINE.slice(typed)}</span>
      </div>
    </AbsoluteFill>
  );
};
