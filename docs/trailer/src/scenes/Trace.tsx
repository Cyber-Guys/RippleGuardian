import React from "react";
import { Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { box, hopBox, mark, src, union, values } from "../captures";
import {
  CameraMove,
  camAt,
  fit,
  type Key,
  within,
} from "../components/CameraMove";
import { Caption } from "../components/Caption";
import { FloatingWindow, VIEW } from "../components/FloatingWindow";
import { Spotlight } from "../components/Spotlight";
import { C, MONO, ramp } from "../theme";
import { at, FPS, has, type SceneProps } from "../timing";

const REC = "rec-trace.webm"; // capture.py retimed the graph to one hop per bar
const HOVERED = "analyst-trace-exchange.png"; // same page, 2x, the pointer on the exchange
const PLAIN = "analyst-trace.png"; // same page, 2x, nothing hovered
const PAGE = { w: 1920, h: 1080 };
const LAG = 3; // frames; puts the exchange tooltip of the recording on the impact
const HOPS = [0, 1, 2, 3, 4];

/** Scene 5, the hero shot: the hop graph draws itself, one hop per bar, then the impact. */
export const Trace: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const impact = at(p, "impact");
  const columns = HOPS.map((h) => hopBox(REC, h));
  // The full cut reaches the impact with the pointer on the exchange (tooltip shown); the
  // 30-second cut hits it the moment the last hop pops, before any hover.
  const hovered = has(p, "muleHover");
  const STILL = hovered ? HOVERED : PLAIN;
  const focus = hovered
    ? union(box(STILL, "exchange"), box(STILL, "exchangeCard"))
    : box(STILL, "exchange");

  // Start close on the victim and follow the newest hops to the right, inside the graph panel;
  // the last hop shows the whole graph, then the camera hits the exchange.
  const panel = box(REC, "panel");
  const keys: Key[] = HOPS.map((h) => {
    const shown = h < 4 ? columns.slice(Math.max(0, h - 2), h + 1) : columns;
    const cam = fit(union(...shown), PAGE, VIEW, 0.2, h < 4 ? 2 : 1.6);
    return {
      at: at(p, `hop${h}`),
      cam: within(cam, panel, PAGE, VIEW),
      dur: 96,
    };
  });
  keys.push({ at: impact, cam: fit(focus, PAGE, VIEW, 0.3), dur: 54 });

  const trim = Math.round(mark(REC, "flowStart") * FPS) - LAG;
  const hit = Math.exp(-Math.max(0, frame - impact) / 14);
  const second = has(p, "traceCaption2") ? at(p, "traceCaption2") : undefined;

  return (
    <>
      <FloatingWindow>
        <CameraMove
          cam={camAt(frame, keys, PAGE, VIEW)}
          page={PAGE}
          view={VIEW}
        >
          {(s) => (
            <>
              <OffthreadVideo
                src={staticFile(src(REC))}
                trimBefore={trim}
                muted
                style={{ position: "absolute", width: PAGE.w, height: PAGE.h }}
              />
              <Img
                src={staticFile(src(STILL))}
                style={{
                  position: "absolute",
                  width: PAGE.w,
                  height: PAGE.h,
                  opacity: ramp(frame, impact + 10, 14),
                }}
              />
              <Spotlight
                box={focus}
                scale={s}
                color={C.danger}
                pad={14}
                pulse={hit}
                opacity={ramp(frame, impact, 10)}
              />
            </>
          )}
        </CameraMove>
      </FloatingWindow>
      <Caption
        eyebrow="ANALYST"
        at={at(p, "traceCaption1")}
        out={impact}
        nextAt={second}
        next={
          <>
            {values.trace.transfers} tainted transfers over {values.trace.hops}{" "}
            hops, every amount read from{" "}
            <span style={{ fontFamily: MONO, fontWeight: 500 }}>
              delivered_amount
            </span>
          </>
        }
      >
        Blockchain forensics: follow the money, hop by hop.
      </Caption>
    </>
  );
};
