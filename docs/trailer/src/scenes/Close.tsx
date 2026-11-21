import React from "react";
import { AbsoluteFill, Img, useCurrentFrame } from "remotion";
import logo from "../../../assets/logo.jpeg";
import { KineticLine } from "../components/KineticLine";
import { C, INTER, ramp } from "../theme";
import { at, type SceneProps } from "../timing";

export const LOGO = { size: 400, top: 140 };
export const TAGLINE = {
  text: "BLOCKCHAIN FORENSICS FRAMEWORK FOR THE XRP LEDGER",
  top: 585,
};
export const CLOSING = { text: "Know the moment your wallet moves.", top: 660 };

/** The logo on the stage; the #logo-key filter (Trailer.tsx) drops its navy square. */
export const Logo: React.FC<{
  size: number;
  top: number;
  opacity?: number;
  scale?: number;
}> = ({ size, top, opacity = 1, scale = 1 }) => (
  <Img
    src={logo}
    style={{
      position: "absolute",
      left: (1920 - size) / 2,
      top,
      width: size,
      height: size,
      opacity,
      transform: `scale(${scale})`,
      filter: "url(#logo-key)",
    }}
  />
);

export const Tagline: React.FC<{ opacity: number }> = ({ opacity }) => (
  <div
    style={{
      position: "absolute",
      top: TAGLINE.top,
      width: "100%",
      textAlign: "center",
      fontFamily: INTER,
      color: C.blue,
      fontSize: 26,
      fontWeight: 600,
      letterSpacing: "0.22em",
      opacity,
    }}
  >
    {TAGLINE.text}
  </div>
);

/** Scene 9: silence, the logo, then the closing line on the final chord. */
export const Close: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const logoIn = ramp(frame, 0, 60);
  return (
    <AbsoluteFill>
      <Logo
        size={LOGO.size}
        top={LOGO.top}
        opacity={logoIn}
        scale={0.96 + 0.04 * logoIn}
      />
      <Tagline opacity={ramp(frame, at(p, "tagline"), 30)} />
      <div
        style={{
          position: "absolute",
          top: CLOSING.top,
          width: "100%",
          textAlign: "center",
        }}
      >
        <KineticLine at={at(p, "finalChord")} size={68}>
          {CLOSING.text}
        </KineticLine>
      </div>
    </AbsoluteFill>
  );
};
