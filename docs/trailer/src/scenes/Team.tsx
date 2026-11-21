import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, INTER, MONO, ramp } from "../theme";
import { at, type SceneProps } from "../timing";
import { CLOSING, Logo, LOGO, Tagline } from "./Close";

const MEMBERS = [
  ["NG", "Nicola Ghisu", "NicoXVI"],
  ["TC", "Tommaso Casti", "t0mm1"],
  ["DO", "Daniele Orrù", "DenInDev"],
  ["AC", "Andrea Cerolini", "percyghost"],
  ["DO", "Diego Oliva", "doliv"],
  ["NM", "Nicholas Meli", "uNickz"],
];

const VENUE = [
  "IXH26 Italian XRPL Hackathon",
  "Track: XRPL applications",
  "Department of Mathematics, University of Bari Aldo Moro · Bari, Italy · 20-21 November 2026",
];

const rise = (e: number): React.CSSProperties => ({
  opacity: e,
  transform: `translateY(${(1 - e) * 12}px)`,
});

/** Scene 10: the logo glides up, the credits build on the beat, fade to black. */
export const Team: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const glide = ramp(frame, at(p, "logoGlide"), 42);
  const leave = 1 - ramp(frame, 0, 14); // tagline and closing line from scene 9
  const fadeAt = at(p, "fadeOut");
  const black = interpolate(frame, [fadeAt, p.duration - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const venueAt = at(p, "venue");
  return (
    <AbsoluteFill style={{ fontFamily: INTER, alignItems: "center" }}>
      <Logo
        size={LOGO.size + (150 - LOGO.size) * glide}
        top={LOGO.top + (40 - LOGO.top) * glide}
      />
      <Tagline opacity={leave} />
      <div
        style={{
          position: "absolute",
          top: CLOSING.top,
          width: "100%",
          textAlign: "center",
          color: C.white,
          fontSize: 68,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          lineHeight: 1.15,
          opacity: leave,
        }}
      >
        {CLOSING.text}
      </div>
      <div
        style={{
          position: "absolute",
          top: 214,
          color: C.white,
          fontSize: 64,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          ...rise(ramp(frame, at(p, "teamTitle"), 24)),
        }}
      >
        Ripple Guardian
      </div>
      <div
        style={{
          position: "absolute",
          top: 300,
          color: C.blue,
          fontSize: 32,
          fontWeight: 500,
          ...rise(ramp(frame, at(p, "teamBy"), 24)),
        }}
      >
        by Team CyberGuys
      </div>
      <div style={{ position: "absolute", top: 410, display: "flex", gap: 22 }}>
        {MEMBERS.map(([initials, name, handle], i) => (
          <div
            key={handle}
            style={{
              width: 262,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              ...rise(ramp(frame, at(p, `member${i + 1}`), 24)),
            }}
          >
            <div
              style={{
                width: 108,
                height: 108,
                borderRadius: 54,
                display: "grid",
                placeItems: "center",
                border: `2px solid ${C.blue}`,
                background: "rgba(94, 162, 245, 0.12)",
                color: C.white,
                fontSize: 38,
                fontWeight: 600,
              }}
            >
              {initials}
            </div>
            <div
              style={{
                marginTop: 20,
                color: C.white,
                fontSize: 27,
                fontWeight: 600,
              }}
            >
              {name}
            </div>
            <div
              style={{
                marginTop: 6,
                color: C.blue,
                fontSize: 22,
                fontFamily: MONO,
              }}
            >
              {handle}
            </div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", top: 780, textAlign: "center" }}>
        {VENUE.map((line) => (
          <div
            key={line}
            style={{
              color: C.mist,
              fontSize: 24,
              lineHeight: 1.6,
              ...rise(0.6 * ramp(frame, venueAt, 24)), // one block, so it reads before the fade
            }}
          >
            {line}
          </div>
        ))}
      </div>
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: black }} />
    </AbsoluteFill>
  );
};
