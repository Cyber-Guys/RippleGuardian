import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { Alert } from "./scenes/Alert";
import { Close } from "./scenes/Close";
import { ColdOpen } from "./scenes/ColdOpen";
import { OwnerKnows } from "./scenes/OwnerKnows";
import { Problem } from "./scenes/Problem";
import { Recovery } from "./scenes/Recovery";
import { Team } from "./scenes/Team";
import { Tour } from "./scenes/Tour";
import { Trace } from "./scenes/Trace";
import { WhyXrpl } from "./scenes/WhyXrpl";
import { C } from "./theme";
import { type CutName, cuts, type SceneProps, sceneOf } from "./timing";

const SCENES: Record<string, React.FC<SceneProps>> = {
  coldOpen: ColdOpen,
  problem: Problem,
  alert: Alert,
  recovery: Recovery,
  trace: Trace,
  ownerKnows: OwnerKnows,
  tour: Tour,
  whyXrpl: WhyXrpl,
  close: Close,
  team: Team,
};

/** Every scene starts on the bar timing.json gives it; the music comes from the same file. */
export const Trailer: React.FC<{ cut: CutName }> = ({ cut: name }) => {
  const cut = cuts[name];
  return (
    <AbsoluteFill style={{ backgroundColor: C.stage }}>
      <svg width={0} height={0} style={{ position: "absolute" }} aria-hidden>
        <filter id="logo-key" colorInterpolationFilters="sRGB">
          {/* alpha from the blue channel: the logo's navy (blue 59 of 255) turns transparent */}
          <feColorMatrix
            type="matrix"
            values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 1.67 0 -0.386"
          />
        </filter>
      </svg>
      <Audio src={staticFile(cut.audio)} />
      {cut.scenes.map((s) => {
        const { from, duration } = sceneOf(cut, s.name);
        const Scene = SCENES[s.name];
        return (
          <Sequence
            key={s.name}
            name={s.name}
            from={from}
            durationInFrames={duration}
          >
            <Scene cut={cut} start={from} duration={duration} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
