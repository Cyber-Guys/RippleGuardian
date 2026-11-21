import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { box, grow, lerpBox, pageOf, src, union } from "../captures";
import { CameraMove, camAt, fit, type Key } from "../components/CameraMove";
import { Caption } from "../components/Caption";
import { FloatingWindow, VIEW } from "../components/FloatingWindow";
import { Spotlight } from "../components/Spotlight";
import { during, ramp } from "../theme";
import { at, type SceneProps } from "../timing";

const PAGE = "owner-recover-full.png";

/** Scene 4: pan down the four recovery steps, one per beat, ending on the PDF report. */
export const Recovery: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const page = pageOf(PAGE);
  const steps = [1, 2, 3, 4].map((i) => box(PAGE, `step${i}`));
  const stepAt = [1, 2, 3, 4].map((i) => at(p, `recoveryStep${i}`));
  const report = at(p, "recoveryReport");
  const pdf = box(PAGE, "pdf");

  const keys: Key[] = [
    {
      at: 0,
      cam: fit(
        union(box(PAGE, "head"), box(PAGE, "timeline")),
        page,
        VIEW,
        0.08,
      ),
    },
    {
      at: stepAt[0] - 90,
      cam: fit(union(...steps), page, VIEW, 0.05),
      dur: 90,
    },
    { at: report, cam: fit(grow(pdf, 150, 90), page, VIEW, 0.1), dur: 60 },
  ];
  let ring = steps[0];
  for (let i = 1; i < steps.length; i++)
    ring = lerpBox(ring, steps[i], ramp(frame, stepAt[i], 12));

  return (
    <>
      <FloatingWindow>
        <CameraMove
          cam={camAt(frame, keys, page, VIEW)}
          page={page}
          view={VIEW}
        >
          {(s) => (
            <>
              <Img
                src={staticFile(src(PAGE))}
                style={{ width: page.w, height: page.h }}
              />
              <Spotlight
                box={ring}
                scale={s}
                dim={false}
                opacity={during(frame, stepAt[0], report + 8)}
              />
              <Spotlight
                box={pdf}
                scale={s}
                opacity={ramp(frame, report, 14)}
                pulse={Math.exp(-Math.max(0, frame - report) / 14)}
              />
            </>
          )}
        </CameraMove>
      </FloatingWindow>
      <Caption eyebrow="OWNER" at={at(p, "recoveryCaption")}>
        A four-step recovery plan and a PDF incident report with a SHA-256
        fingerprint.
      </Caption>
    </>
  );
};
