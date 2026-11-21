import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { box, pageOf, src } from "../captures";
import {
  CameraMove,
  camAt,
  fit,
  type Key,
  whole,
} from "../components/CameraMove";
import { Caption } from "../components/Caption";
import { FloatingWindow, VIEW } from "../components/FloatingWindow";
import { glide } from "../theme";
import { at, type SceneProps } from "../timing";

// `left`: frame only the left part of a full-width panel, where its labels are, so the push-in
// gets close enough to read them.
const FEATURES = [
  {
    file: "auth-register.png",
    key: "card",
    area: "OWNER",
    title: "Sign up with just a username: no email or phone number needed.",
    left: 1,
    widen: 560,
  },
  {
    file: "owner-watch.png",
    key: "watch",
    area: "OWNER",
    title: "Watch any wallet, live from the ledger.",
    left: 1,
  },
  {
    file: "owner-verify.png",
    key: "status",
    area: "OWNER",
    title: "Prove you own it with a one-drop payment.",
    left: 0.5,
  },
  {
    file: "analyst-findings.png",
    key: "table",
    area: "ANALYST",
    title: "Four detectors raise findings to review.",
    left: 0.62,
  },
  {
    file: "analyst-flags.png",
    key: "form",
    area: "ANALYST",
    title:
      "Flags signed with the analyst's name, checked by every user before paying.",
    left: 0.55,
  },
  {
    file: "analyst-settings.png",
    key: "first",
    area: "ANALYST",
    title: "Tune every detector rule.",
    left: 0.6,
  },
  {
    file: "analyst-lookup.png",
    key: "result",
    area: "ANALYST",
    title: "Look up any validated transaction.",
    left: 0.55,
  },
];

/** Scene 7: one capture, one push-in, one caption per feature; a cut on every change. */
export const Tour: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  const starts = FEATURES.map((_, i) => at(p, `tour${i + 1}`));
  const i = Math.max(0, starts.filter((s) => frame >= s).length - 1);
  const f = FEATURES[i];
  const from = starts[i];
  const to = i + 1 < starts.length ? starts[i + 1] : p.duration;
  const page = pageOf(f.file);
  const target = box(f.file, f.key);
  const widen = ("widen" in f ? f.widen : undefined) ?? 0; // reveal more of the card to the left
  const focus = {
    ...target,
    x: target.x - widen,
    w: target.w * f.left + widen,
  };
  // Each shot opens already halfway in and closes in slowly, so no big zoom follows the cut.
  const end = fit(focus, page, VIEW, 0.16);
  const open = whole(page);
  const start = {
    x: open.x + (end.x - open.x) * 0.6,
    y: open.y + (end.y - open.y) * 0.6,
    z: Math.exp(Math.log(end.z) * 0.55),
  };
  const keys: Key[] = [
    { at: from, cam: start },
    { at: from, cam: end, dur: Math.min(110, to - from - 10) },
  ];
  const cam = camAt(frame, keys, page, VIEW);
  const drift = 1 + 0.03 * glide(frame, from, to - from); // keeps creeping in until the cut
  // Hard cut on the downbeat (the whoosh peaks there), then the push-in.
  return (
    <>
      <FloatingWindow>
        <CameraMove cam={{ ...cam, z: cam.z * drift }} page={page} view={VIEW}>
          {() => (
            <Img
              src={staticFile(src(f.file))}
              style={{ width: page.w, height: page.h }}
            />
          )}
        </CameraMove>
      </FloatingWindow>
      <Caption key={f.file} eyebrow={f.area} at={from} out={to}>
        {f.title}
      </Caption>
    </>
  );
};
