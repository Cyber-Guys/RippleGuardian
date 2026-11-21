import timing from "../timing.json";

export type Event = { name: string; bar: number; beat: number; nodes?: number };
export type Span = { name: string; from: number; to: number };
export type Cut = {
  bars: number;
  frames: number;
  audio: string;
  scenes: Span[];
  events: Event[];
};
export type CutName = "full" | "short";

export const FPS: number = timing.fps;
export const BEAT: number = timing.beatFrames;
export const BAR: number = timing.barFrames;
export const EIGHTH = BEAT / 2;
export const cuts = timing.cuts as unknown as Record<CutName, Cut>;

/** Bars and beats are 1-based; beat 1.5 is the eighth note after beat 1. */
export const frameOf = (bar: number, beat = 1): number =>
  Math.round((bar - 1) * BAR + (beat - 1) * BEAT);

export const sceneOf = (cut: Cut, name: string) => {
  const s = cut.scenes.find((x) => x.name === name);
  if (!s) throw new Error(`timing.json: no scene "${name}"`);
  return {
    from: frameOf(s.from),
    duration: frameOf(s.to + 1) - frameOf(s.from),
  };
};

export type SceneProps = { cut: Cut; start: number; duration: number };

/** Frame of a timing.json event, relative to the start of the scene. */
export const at = (p: SceneProps, name: string): number => {
  const e = p.cut.events.find((x) => x.name === name);
  if (!e) throw new Error(`timing.json: no event "${name}"`);
  return frameOf(e.bar, e.beat) - p.start;
};

export const has = (p: SceneProps, name: string): boolean =>
  p.cut.events.some((x) => x.name === name);
