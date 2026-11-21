import React from "react";
import { useCurrentFrame } from "remotion";
import { C, INTER, ramp } from "../theme";

type Props = {
  children: React.ReactNode;
  at: number;
  size?: number;
  color?: string;
  weight?: number;
  dim?: number; // multiplies the opacity, to push a line back
  style?: React.CSSProperties;
};

/** A large line of type that lands with a 12 px rise and a fade. */
export const KineticLine: React.FC<Props> = ({
  children,
  at,
  size = 84,
  color = C.white,
  weight = 600,
  dim = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, at, 30);
  return (
    <div
      style={{
        fontFamily: INTER,
        fontSize: size,
        fontWeight: weight,
        color,
        lineHeight: 1.15,
        letterSpacing: "-0.02em",
        opacity: p * dim,
        transform: `translateY(${(1 - p) * 12}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
