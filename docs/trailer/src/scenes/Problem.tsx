import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { KineticLine } from "../components/KineticLine";
import { C, ramp } from "../theme";
import { at, type SceneProps } from "../timing";

const LINES = [
  "A new key is added.",
  "The wallet is drained.",
  "The XRP is on an exchange in minutes.",
];

/** Scene 2: one line per kick, then the red one while the others step back. */
export const Problem: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const red = at(p, "problemRed");
  const dim = 1 - 0.65 * ramp(frame, red, 24);
  return (
    <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 200 }}>
      {LINES.map((line, i) => (
        <KineticLine
          key={line}
          at={at(p, `problem${i + 1}`)}
          dim={dim}
          style={{ marginBottom: 18 }}
        >
          {line}
        </KineticLine>
      ))}
      <KineticLine
        at={red}
        color={C.danger}
        style={{ marginTop: 40, textShadow: `0 0 48px ${C.glow}` }}
      >
        Most owners find out in the morning.
      </KineticLine>
    </AbsoluteFill>
  );
};
