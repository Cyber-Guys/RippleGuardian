import React from "react";
import { Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { box, mark, src, union } from "../captures";
import { CameraMove, camAt, fit, type Key } from "../components/CameraMove";
import { Caption } from "../components/Caption";
import { FloatingWindow, VIEW } from "../components/FloatingWindow";
import { Spotlight } from "../components/Spotlight";
import { glide, ramp } from "../theme";
import { at, FPS, type SceneProps } from "../timing";

const REC = "rec-notification.webm";
const STILL = "owner-notifications.png"; // same page, 2x, the alert expanded
const EXPLORER = "explorer-deposit.png";
const PAGE = { w: 1920, h: 1080 };
const EXP = { w: 1180, h: (1180 * 9) / 16 };

/** Scene 6: the "Stolen funds located" alert opens on the downbeat, then the same deposit on
 * testnet.xrpl.org slides in over it. */
export const OwnerKnows: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const expand = at(p, "notifExpand");
  const explorer = at(p, "explorer");
  const tagAt = at(p, "explorerTag");

  // Play the recording so that the pointer reaches the alert exactly on `expand`; the page is
  // on screen from about 0.5 s into the recording.
  const hover = mark(REC, "hover");
  const v0 = Math.max(0.6, hover - expand / FPS);
  const rate = (hover - v0) / (expand / FPS);

  const item = box(REC, "item");
  const keys: Key[] = [
    {
      at: 0,
      cam: fit(
        { ...item, w: item.w * 0.6, y: item.y - 60, h: item.h + 160 },
        PAGE,
        VIEW,
        0.05,
        1.7,
      ),
    },
    {
      at: expand + 4,
      cam: fit(box(STILL, "message"), PAGE, VIEW, 0.3),
      dur: 72,
    },
  ];
  const row = box(EXPLORER, "row");
  const expKeys: Key[] = [
    {
      at: explorer,
      cam: fit(union(box(EXPLORER, "status"), row), PAGE, EXP, 0.12),
    },
    { at: tagAt, cam: fit(row, PAGE, EXP, 0.25), dur: 60 },
  ];
  const slide = glide(frame, explorer, 54);

  return (
    <>
      <FloatingWindow opacity={1 - 0.35 * slide} scale={1 - 0.02 * slide}>
        <CameraMove
          cam={camAt(frame, keys, PAGE, VIEW)}
          page={PAGE}
          view={VIEW}
        >
          {() => (
            <>
              <OffthreadVideo
                src={staticFile(src(REC))}
                trimBefore={Math.round(v0 * FPS)}
                playbackRate={rate}
                muted
                style={{ position: "absolute", width: PAGE.w, height: PAGE.h }}
              />
              <Img
                src={staticFile(src(STILL))}
                style={{
                  position: "absolute",
                  width: PAGE.w,
                  height: PAGE.h,
                  opacity: ramp(frame, expand + 22, 12),
                }}
              />
            </>
          )}
        </CameraMove>
      </FloatingWindow>
      {frame >= explorer ? (
        <FloatingWindow
          x={1920 - EXP.w - 150 + (1 - slide) * 900}
          y={150}
          width={EXP.w}
          enter={slide}
        >
          <CameraMove
            cam={camAt(frame, expKeys, PAGE, EXP)}
            page={PAGE}
            view={EXP}
          >
            {(s) => (
              <>
                <Img
                  src={staticFile(src(EXPLORER))}
                  style={{ width: PAGE.w, height: PAGE.h }}
                />
                <Spotlight
                  box={box(EXPLORER, "tag")}
                  scale={s}
                  pad={10}
                  opacity={ramp(frame, tagAt, 14)}
                  pulse={Math.exp(-Math.max(0, frame - tagAt) / 14)}
                />
              </>
            )}
          </CameraMove>
        </FloatingWindow>
      ) : null}
      <Caption eyebrow="OWNER" at={at(p, "notifCaption")}>
        The exact destination tag: the customer account the exchange can freeze.
      </Caption>
    </>
  );
};
