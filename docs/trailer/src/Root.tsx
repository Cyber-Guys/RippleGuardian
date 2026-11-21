import React from "react";
import { Composition } from "remotion";
import { Trailer } from "./Trailer";
import { cuts, FPS } from "./timing";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Trailer"
      component={Trailer}
      durationInFrames={cuts.full.frames}
      fps={FPS}
      width={1920}
      height={1080}
      defaultProps={{ cut: "full" as const }}
    />
    <Composition
      id="Trailer30"
      component={Trailer}
      durationInFrames={cuts.short.frames}
      fps={FPS}
      width={1920}
      height={1080}
      defaultProps={{ cut: "short" as const }}
    />
  </>
);
