import React from "react";
import {
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { box, lerpBox, mark, pageOf, src } from "../captures";
import {
  CameraMove,
  camAt,
  fit,
  type Key,
  whole,
} from "../components/CameraMove";
import { Caption } from "../components/Caption";
import { FloatingWindow, VIEW } from "../components/FloatingWindow";
import { Spotlight } from "../components/Spotlight";
import { C, during, ramp } from "../theme";
import { at, BEAT, FPS, has, type SceneProps } from "../timing";

const DASH = "owner-dashboard.png";
const REC = "rec-what-to-do.webm";

/** Scene 3: alice's dashboard in the compromised state; the recorded cursor clicks What to do. */
export const Alert: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const page = pageOf(DASH);
  const click = at(p, "whatToDoClick");
  const spot = has(p, "whatToDo") ? at(p, "whatToDo") : click - 90;
  const feedAt = has(p, "alertFeedKey") ? at(p, "alertFeedKey") : null;
  const sentAt = has(p, "alertFeedSent") ? at(p, "alertFeedSent") : null;
  const status = box(DASH, "status");
  const words = { ...status, w: status.w * 0.55 }; // shield, headline and detail
  const actions = {
    ...status,
    x: status.x + status.w * 0.45,
    w: status.w * 0.55,
  };

  const keys: Key[] = [
    { at: 0, cam: whole(page) },
    { at: 8, cam: fit(words, page, VIEW, 0.12), dur: 52 },
  ];
  if (feedAt !== null)
    keys.push({ at: feedAt, cam: fit(box(DASH, "feed"), page, VIEW, 0.12) });
  keys.push({ at: spot, cam: fit(actions, page, VIEW, 0.2, 1.5) });
  // The click opens the recovery page: pull back so it lands full frame for scene 4.
  keys.push({ at: click + 12, cam: whole(page), dur: 42 });

  const pulse = Math.exp(-(frame % (2 * BEAT)) / 10); // kick on beats 1 and 3
  const ring =
    feedAt === null
      ? null
      : lerpBox(
          box(DASH, "alertKey"),
          box(DASH, "alertSent"),
          sentAt === null ? 0 : ramp(frame, sentAt, 18),
        );
  // The recording starts at `spot`, trimmed so that its click lands on the downbeat.
  const trim = Math.round(mark(REC, "click") * FPS - (click - spot));

  return (
    <>
      <FloatingWindow enter={ramp(frame, 0, 30)}>
        <CameraMove cam={camAt(frame, keys)} page={page} view={VIEW}>
          {(s) => (
            <>
              <Img
                src={staticFile(src(DASH))}
                style={{ width: page.w, height: page.h }}
              />
              <Sequence from={spot} layout="none">
                <OffthreadVideo
                  src={staticFile(src(REC))}
                  trimBefore={trim}
                  muted
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    width: page.w,
                    height: page.h,
                    opacity: ramp(frame, spot, 12),
                  }}
                />
              </Sequence>
              <Spotlight
                box={status}
                scale={s}
                dim={false}
                color={C.danger}
                pulse={pulse}
                opacity={(0.35 + 0.65 * pulse) * (1 - ramp(frame, spot, 12))}
              />
              {ring !== null && feedAt !== null ? (
                <Spotlight
                  box={ring}
                  scale={s}
                  dim={false}
                  opacity={during(frame, feedAt, spot)}
                />
              ) : null}
              <Spotlight
                box={box(DASH, "whatToDo")}
                scale={s}
                color={C.danger}
                opacity={during(frame, spot + 6, click + 30)}
              />
            </>
          )}
        </CameraMove>
      </FloatingWindow>
      <Caption eyebrow="OWNER" at={at(p, "alertCaption")}>
        Alerts in plain words, the moment it happens.
      </Caption>
    </>
  );
};
