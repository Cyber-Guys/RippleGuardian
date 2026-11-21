import React from "react";
import { useCurrentFrame } from "remotion";
import { C, INTER, ramp } from "../theme";
import { EIGHTH } from "../timing";
import { VIEW, WIN } from "./FloatingWindow";

type Props = {
  eyebrow?: string; // the area, e.g. OWNER or ANALYST
  children: React.ReactNode; // the white title line
  at: number;
  out?: number; // fully gone at this frame
  next?: React.ReactNode; // a second title that replaces the first under the same eyebrow
  nextAt?: number;
};

/** Bottom-left feature caption: blue eyebrow, then the title an eighth note later. */
export const Caption: React.FC<Props> = ({
  eyebrow,
  children,
  at,
  out,
  next,
  nextAt,
}) => {
  const frame = useCurrentFrame();
  const show = (start: number, end?: number): React.CSSProperties => {
    const p = ramp(frame, start, 24);
    const gone = end === undefined ? 0 : ramp(frame, end - 12, 12);
    return {
      opacity: p * (1 - gone),
      transform: `translateY(${(1 - p) * 12}px)`,
    };
  };
  const titleAt = eyebrow ? at + EIGHTH : at;
  const title: React.CSSProperties = {
    gridArea: "1 / 1",
    color: C.white,
    fontSize: 38,
    fontWeight: 600,
    lineHeight: 1.22,
    letterSpacing: "-0.01em",
  };
  return (
    <div
      style={{
        position: "absolute",
        left: WIN.x,
        bottom: 46,
        width: VIEW.w,
        fontFamily: INTER,
      }}
    >
      {eyebrow ? (
        <div
          style={{
            ...show(at, out),
            color: C.blue,
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "0.16em",
            marginBottom: 10,
          }}
        >
          {eyebrow}
        </div>
      ) : null}
      <div style={{ display: "grid" }}>
        <div style={{ ...title, ...show(titleAt, nextAt ?? out) }}>
          {children}
        </div>
        {next !== undefined && nextAt !== undefined ? (
          <div style={{ ...title, ...show(nextAt, out) }}>{next}</div>
        ) : null}
      </div>
    </div>
  );
};
