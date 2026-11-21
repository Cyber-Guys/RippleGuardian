"""Original soundtrack for the trailer, synthesized from scratch with numpy.

    uv run --with numpy python docs/trailer/audio/make_music.py

Writes public/music.wav (90 s) and public/music-30s.wav (30 s): 48 kHz, 16-bit stereo,
120 BPM, D minor. Every part and every hit (chime, node ticks, impact, whooshes, cards, team
plucks) is placed from timing.json, the file the video reads too. No samples, no presets:
oscillators, envelopes, one-pole filters, a feedback delay and a small Schroeder reverb.
"""

from __future__ import annotations

import json
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TRAILER = HERE.parent
T = json.loads((TRAILER / "timing.json").read_text())
SR: int = T["sampleRate"]
BEAT = SR * 60 // T["bpm"]  # 24000 samples
BAR = 4 * BEAT
CEILING = 10 ** (-1 / 20)  # -1 dBFS
rng = np.random.default_rng(20261121)

# Dm - Bb - F - C, restarted at the first bar of each part.
PROGRESSION = [
    [50, 57, 62, 65, 69],  # Dm: D3 A3 D4 F4 A4
    [46, 53, 58, 62, 65],  # Bb: Bb2 F3 Bb3 D4 F4
    [53, 57, 60, 65, 69],  # F:  F3 A3 C4 F4 A4
    [48, 55, 60, 64, 67],  # C:  C3 G3 C4 E4 G4
]
ROOTS = [38, 34, 41, 36]  # D2 Bb1 F2 C2
DRONE = [38, 45, 50]  # D2 A2 D3
FINAL = [46, 53, 60, 62, 65, 70]  # Bb add9
OUTRO = [41, 48, 55, 57, 60, 65]  # F add9
TICKS = [86, 89, 93, 96, 98]  # D6 F6 A6 C7 D7
STEPS = [86, 88, 89, 91, 93]  # D6 E6 F6 G6 A6
TEAM = [77, 79, 81, 84, 86, 89]  # F5 G5 A5 C6 D6 F6


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def at(bar: float, beat: float = 1) -> int:
    return round(((bar - 1) * 4 + (beat - 1)) * BEAT)


def secs(n: float) -> np.ndarray:
    return np.arange(int(n * SR)) / SR


# ----- building blocks --------------------------------------------------------------------


def saw(freq: float, n: int) -> np.ndarray:
    """Band-limited (PolyBLEP) sawtooth with a random start phase."""
    dt = freq / SR
    ph = (rng.random() + dt * np.arange(n)) % 1.0
    y = 2 * ph - 1
    lo = ph < dt
    t = ph[lo] / dt
    y[lo] -= 2 * t - t * t - 1
    hi = ph > 1 - dt
    t = (ph[hi] - 1) / dt
    y[hi] -= t * t + 2 * t + 1
    return y


def lowpass(x: np.ndarray, cutoff: float | np.ndarray) -> np.ndarray:
    """One-pole low-pass; `cutoff` in Hz, a constant or one value per sample."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = (1 - np.exp(-2 * np.pi * c / SR)).tolist()
    out, y = [], 0.0
    for xi, ai in zip(x.tolist(), a, strict=True):
        y += ai * (xi - y)
        out.append(y)
    return np.array(out)


def highpass(x: np.ndarray, cutoff: float | np.ndarray) -> np.ndarray:
    return x - lowpass(x, cutoff)


def comb(x: np.ndarray, d: int, g: float) -> np.ndarray:
    """y[n] = x[n] + g y[n-d], computed one block of d samples at a time."""
    y = np.zeros_like(x)
    for s in range(0, len(x), d):
        e = min(s + d, len(x))
        y[s:e] = x[s:e] + (g * y[s - d : e - d] if s >= d else 0)
    return y


def allpass(x: np.ndarray, d: int, g: float) -> np.ndarray:
    y = np.zeros_like(x)
    for s in range(0, len(x), d):
        e = min(s + d, len(x))
        y[s:e] = -g * x[s:e]
        if s >= d:
            y[s:e] += x[s - d : e - d] + g * y[s - d : e - d]
    return y


def reverb(x: np.ndarray) -> np.ndarray:
    """Small stereo Schroeder reverb: 4 combs and 2 allpasses per side, darkened."""
    out = np.zeros_like(x)
    for ch, spread in ((0, 0), (1, 23)):
        wet = sum(comb(x[:, ch], d + spread, 0.82) for d in (1214, 1390, 1548, 1695)) / 4
        for d in (605, 245):
            wet = allpass(wet, d + spread, 0.5)
        out[:, ch] = lowpass(wet, 5200)
    return out


def echo(x: np.ndarray) -> np.ndarray:
    """Feedback delay, dotted eighth on the left and a quarter on the right."""
    return np.stack([comb(x[:, 0], BEAT * 3 // 4, 0.38), comb(x[:, 1], BEAT, 0.32)], axis=1) - x


def pan(sig: np.ndarray, p: float) -> np.ndarray:
    """Mono to stereo, equal power, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], axis=1)


def add(bus: np.ndarray, sig: np.ndarray, start: int, gain: float = 1.0) -> None:
    """Mix `sig` (mono or stereo) into `bus` at sample `start`, cut at the bus end."""
    if sig.ndim == 1:
        sig = pan(sig, 0)
    if start >= len(bus):
        return
    end = min(len(bus), start + len(sig))
    bus[start:end] += gain * sig[: end - start]


def fade_ends(x: np.ndarray, ms: float = 3) -> np.ndarray:
    n = min(len(x) // 2, int(ms * SR / 1000))
    ramp = np.linspace(0, 1, n)
    x = x.copy()
    x[:n] *= ramp[:, None] if x.ndim == 2 else ramp
    x[len(x) - n :] *= ramp[::-1, None] if x.ndim == 2 else ramp[::-1]
    return x


# ----- instruments ------------------------------------------------------------------------


def kick(soft: bool = False) -> np.ndarray:
    t = secs(0.5)
    f = (42 if soft else 48) + ((110 if soft else 150) - (42 if soft else 48)) * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.3 if soft else 0.22))
    click = 0 if soft else 0.28 * np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.004)
    noise = 0 if soft else 0.2 * highpass(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.003)
    return fade_ends(np.tanh(1.6 * (body + click + noise)) / np.tanh(1.6))


def hat(open_: bool = False) -> np.ndarray:
    t = secs(0.4 if open_ else 0.09)
    noise = highpass(rng.standard_normal(len(t)), 7000)
    return fade_ends(noise * np.exp(-t / (0.11 if open_ else 0.022)))


def clap() -> np.ndarray:
    t = secs(0.35)
    noise = rng.standard_normal(len(t))
    env = sum(np.where(t >= o, np.exp(-(t - o) / 0.004), 0) for o in (0, 0.009, 0.019))
    env += np.where(t >= 0.019, 0.6 * np.exp(-(t - 0.019) / 0.11), 0)
    band = highpass(lowpass(noise * env, 5200), 850)
    tone = 0.3 * np.sin(2 * np.pi * 196 * t) * np.exp(-t / 0.05)
    return fade_ends(band * 1.4 + tone)


def bass_note(midi: int, dur: float) -> np.ndarray:
    t = secs(dur)
    f = hz(midi)
    env = np.minimum(1, t / 0.006) * np.exp(-t / max(dur, 0.25))
    sub = np.sin(2 * np.pi * f * t)
    grit = np.tanh(2.5 * np.sin(2 * np.pi * f * t + 0.4 * np.sin(4 * np.pi * f * t)))
    return fade_ends((0.85 * sub + 0.4 * lowpass(grit, 900)) * env, 6)


def bell(midi: float, dur: float = 2.6) -> np.ndarray:
    t = secs(dur)
    f = hz(midi)
    partials = (
        (1, 1.0, 1.4),
        (2, 0.4, 0.8),
        (2.76, 0.28, 0.5),
        (5.4, 0.12, 0.22),
        (8.93, 0.05, 0.1),
    )
    y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in partials)
    return fade_ends(y * np.minimum(1, t / 0.002))


def pluck(midi: float, dur: float = 1.4) -> np.ndarray:
    t = secs(dur)
    f = hz(midi)
    y = sum(
        np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.2 + 1.7 * k)) / k
        for k in range(1, 11)
        if f * k < 14000
    )
    return fade_ends(y * np.minimum(1, t / 0.003))


def tick(midi: float) -> np.ndarray:
    t = secs(0.14)
    y = np.sin(2 * np.pi * hz(midi) * t) * np.exp(-t / 0.014)
    y += 0.25 * highpass(rng.standard_normal(len(t)), 5000) * np.exp(-t / 0.0012)
    return fade_ends(y)


def blip(midi: float) -> np.ndarray:
    t = secs(0.3)
    f = hz(midi)
    y = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.06)
    return fade_ends(y * np.minimum(1, t / 0.002))


def ui_click() -> np.ndarray:
    t = secs(0.12)
    y = 0.6 * highpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.0015)
    return fade_ends(y + 0.5 * np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.025))


def whoosh(dur: float = 0.55, peak: float = 0.38) -> np.ndarray:
    t = secs(dur)
    env = np.where(t < peak, (t / peak) ** 3, np.exp(-(t - peak) / 0.07))
    sides = []
    for _ in range(2):
        noise = rng.standard_normal(len(t))
        sides.append(highpass(lowpass(noise, 350 + 5200 * env), 250) * env)
    sweep = np.linspace(-0.7, 0.7, len(t))
    left, right = (
        sides[0] * np.cos((sweep + 1) * np.pi / 4),
        sides[1] * np.sin((sweep + 1) * np.pi / 4),
    )
    return fade_ends(np.stack([left, right], axis=1))


def riser(dur_samples: int) -> np.ndarray:
    t = np.arange(dur_samples) / SR
    k = t / t[-1]
    sides = []
    for _ in range(2):
        noise = rng.standard_normal(len(t))
        sides.append(highpass(lowpass(noise, 300 * 30**k), 120 * 12**k))
    tone = np.sin(2 * np.pi * np.cumsum(hz(50) * 4**k) / SR)  # D3 gliding up two octaves
    body = np.stack(sides, axis=1) * 0.8 + pan(tone * 0.25, 0)
    out = body * (k**2.6)[:, None]
    return fade_ends(out, 2)


def impact() -> np.ndarray:
    t = secs(4.5)
    f = 30 + 75 * np.exp(-t / 0.25)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.3)
    burst = lowpass(rng.standard_normal(len(t)), 1100) * np.exp(-t / 0.14) * 2.2
    crack = highpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.012) * 0.5
    y = np.tanh(1.3 * (boom + burst + crack))
    y[0] = y[0] or 1e-3  # the onset check below looks for the first non-zero sample
    return y


def chord_pad(
    notes: list[int], n: int, cutoff: float | np.ndarray, width: float = 0.6
) -> np.ndarray:
    """Detuned saw pad: three voices per note, spread across the stereo field."""
    left, right = np.zeros(n), np.zeros(n)
    for midi in notes:
        for detune, p in ((-0.11, -width), (0.0, 0.0), (0.11, width)):
            v = saw(hz(midi + detune), n)
            a = (p + 1) * np.pi / 4
            left += v * np.cos(a)
            right += v * np.sin(a)
    scale = 1 / (3 * len(notes)) ** 0.5
    return (
        np.stack(
            [lowpass(lowpass(left, cutoff), cutoff), lowpass(lowpass(right, cutoff), cutoff)],
            axis=1,
        )
        * scale
    )


# ----- the score --------------------------------------------------------------------------


class Score:
    def __init__(self, cut: dict) -> None:
        self.cut = cut
        self.n = cut["bars"] * BAR
        self.drums = np.zeros((self.n, 2))
        self.pad = np.zeros((self.n, 2))
        self.bass = np.zeros((self.n, 2))
        self.fx = np.zeros((self.n, 2))
        self.verb = np.zeros((self.n, 2))  # reverb send
        self.delay = np.zeros((self.n, 2))  # echo send
        self.impact = np.zeros(self.n)  # dry impact, for the onset check
        self.kicks: list[int] = []
        self.samples = {
            "kick": kick(),
            "soft": kick(soft=True),
            "hats": [hat() for _ in range(4)],
            "open": hat(open_=True),
            "clap": clap(),
        }
        self.cache: dict[tuple, np.ndarray] = {}

    def note(self, fn: Callable[..., np.ndarray], *args: object) -> np.ndarray:
        key = (fn.__name__, *args)
        if key not in self.cache:
            self.cache[key] = fn(*args)
        return self.cache[key]

    # drums and bass -------------------------------------------------------------------------

    def kick(self, pos: int, soft: bool = False, gain: float = 1.0) -> None:
        add(
            self.drums,
            self.samples["soft" if soft else "kick"],
            pos,
            (0.75 if soft else 0.95) * gain,
        )
        self.kicks.append(pos)

    def hats(self, a: int, b: int, step: float, gain: float, offbeat_only: bool = False) -> None:
        for bar in range(a, b + 1):
            beat = 1.0
            i = 0
            while beat < 5 - 1e-9:
                frac = beat % 1
                accent = {0.0: 0.7, 0.5: 1.0}.get(frac, 0.45)  # offbeat eighths lead
                if not offbeat_only or frac == 0.5:
                    hit = self.samples["hats"][i % 4]
                    add(
                        self.drums,
                        pan(hit, 0.25),
                        at(bar, beat),
                        gain * accent * rng.uniform(0.8, 1.0),
                    )
                beat += step
                i += 1

    def bassline(
        self, a: int, b: int, pattern: list[tuple[float, float, int]], gain: float
    ) -> None:
        """pattern: (beat, length in beats, octave shift) repeated every bar on the bar's root."""
        for bar in range(a, b + 1):
            root = ROOTS[(bar - a) % 4]
            for beat, length, octave in pattern:
                add(
                    self.bass,
                    self.note(bass_note, root + 12 * octave, length * BEAT / SR),
                    at(bar, beat),
                    gain,
                )

    def pads(
        self,
        a: int,
        b: int,
        cutoff: tuple[float, float],
        gain: float,
        chords: list[list[int]] | None = None,
    ) -> None:
        """One chord per bar with overlapping attack and release; cutoff ramps across the part."""
        span = b - a + 1
        for i, bar in enumerate(range(a, b + 1)):
            notes = chords[i % len(chords)] if chords else PROGRESSION[i % 4]
            n = BAR + SR // 2
            c0 = cutoff[0] + (cutoff[1] - cutoff[0]) * i / span
            c1 = cutoff[0] + (cutoff[1] - cutoff[0]) * (i + 1) / span
            c = np.concatenate([np.linspace(c0, c1, BAR), np.full(n - BAR, c1)])
            t = np.arange(n) / SR
            env = np.minimum(1, t / 0.25) * np.where(
                t < BAR / SR, 1, np.exp(-(t - BAR / SR) / 0.12)
            )
            sig = chord_pad(notes, n, c) * env[:, None]
            add(self.pad, sig, at(bar), gain)
            add(self.verb, sig, at(bar), gain * 0.35)

    # parts --------------------------------------------------------------------------------

    def part(self, name: str, a: int, b: int) -> None:
        getattr(self, f"part_{name}")(a, b)

    def part_intro(self, a: int, b: int) -> None:
        self.pads(a, b, (260, 420), 0.1, [DRONE])  # near silence: the chime carries it

    def part_heartbeat(self, a: int, b: int) -> None:
        self.pads(a, b, (420, 520), 0.18, [DRONE])
        for bar in range(a, b + 1):
            for beat in (1, 3):
                self.kick(at(bar, beat), soft=True, gain=0.7)
                add(self.bass, self.note(bass_note, 38, 0.4), at(bar, beat), 0.4)

    def part_tension(self, a: int, b: int) -> None:
        self.pads(a, b, (600, 1700), 0.26)
        for bar in range(a, b + 1):
            for beat in (1, 3):
                self.kick(at(bar, beat), gain=0.72)
        self.hats(a, b - 1, 0.5, 0.10)
        self.hats(b, b, 0.25, 0.10)
        self.bassline(a, b, [(1, 1, 0), (2, 1, 0), (3, 1, 0), (4, 1, 0)], 0.42)

    def part_riser(self, a: int, b: int) -> None:
        self.pads(a, b, (1700, 2600), 0.30)
        for bar in range(a, b + 1):
            for beat in (1, 3):
                self.kick(at(bar, beat), gain=0.85)
        self.hats(a, b, 0.25, 0.09)
        self.bassline(a, b, [(1, 2, 0), (3, 2, 0)], 0.42)
        add(self.fx, riser(at(b + 1) - at(a)), at(a), 0.42)

    def part_drop(self, a: int, b: int) -> None:
        self.pads(a, b, (2600, 3000), 0.34)
        for bar in range(a, b + 1):
            for beat in (1, 2, 3, 4):
                self.kick(at(bar, beat))
            for beat in (2, 4):
                add(self.drums, self.samples["clap"], at(bar, beat), 0.42)
                add(self.verb, self.samples["clap"], at(bar, beat), 0.25)
        self.hats(a, b, 0.5, 0.13, offbeat_only=True)
        self.hats(a, b, 0.25, 0.05)
        self.bassline(a, b, [(1 + i / 2, 0.45, i % 2) for i in range(8)], 0.46)

    def part_impact(self, a: int, b: int) -> None:
        self.pads(a, b, (2000, 1400), 0.34)
        self.bassline(a, b, [(1, 4, 0)], 0.5)
        self.hats(a, b, 0.5, 0.05, offbeat_only=True)

    def part_thin(self, a: int, b: int) -> None:
        self.pads(a, b, (1400, 1500), 0.26)
        for bar in range(a, b + 1):
            self.kick(at(bar, 1), gain=0.65)
        self.hats(a, b, 1.0, 0.07)
        self.bassline(a, b, [(1, 4, 0)], 0.42)

    def part_groove(self, a: int, b: int) -> None:
        self.pads(a, b, (2200, 2600), 0.30)
        for bar in range(a, b + 1):
            for beat in (1, 2, 3, 4):
                self.kick(at(bar, beat), gain=0.92)
            for beat in (2, 4):
                add(self.drums, self.samples["clap"], at(bar, beat), 0.36)
                add(self.verb, self.samples["clap"], at(bar, beat), 0.2)
            add(self.drums, pan(self.samples["open"], 0.3), at(bar, 4.5), 0.07)
        self.hats(a, b, 0.5, 0.11)
        groove = [
            (1, 0.7, 0),
            (1.75, 0.45, 0),
            (2.5, 0.45, 1),
            (3, 0.7, 0),
            (3.75, 0.45, 0),
            (4.5, 0.45, 1),
        ]
        self.bassline(a, b, groove, 0.44)

    def part_build(self, a: int, b: int) -> None:
        self.pads(a, b, (2200, 4200), 0.32)
        for bar in range(a, b + 1):
            for beat in (1, 2, 3, 4):
                self.kick(at(bar, beat), gain=0.92)
            for beat in (2, 4):
                add(self.drums, self.samples["clap"], at(bar, beat), 0.36)
        self.hats(a, b, 0.25, 0.09)
        self.bassline(a, b, [(1 + i / 2, 0.45, 0) for i in range(8)], 0.44)
        for i in range(16):  # snare roll on the last bar, sixteenths, crescendo
            add(self.drums, self.samples["clap"], at(b + i / 16), 0.1 + 0.3 * i / 16)
        add(self.fx, riser(at(b + 1) - at(b - 1)), at(b - 1), 0.38)

    def part_silence(self, a: int, b: int) -> None:
        pass  # enforced on the master: every bus is cut at the first sample of the part

    def part_final(self, a: int, b: int) -> None:
        n = at(b + 1) - at(a) + SR
        t = np.arange(n) / SR
        hold = (at(b + 1) - at(a)) / SR
        env = np.minimum(1, t / 0.9) * np.where(t < hold, 1, np.exp(-(t - hold) / 0.35))
        sig = chord_pad(FINAL, n, 2400, 0.75) * env[:, None]
        sub = np.sin(2 * np.pi * hz(34) * t) * env * 0.5
        add(self.pad, sig + pan(sub, 0), at(a), 0.42)
        add(self.verb, sig, at(a), 0.5)

    def part_outro(self, a: int, b: int) -> None:
        n = at(b + 1) - at(a)
        t = np.arange(n) / SR
        env = np.minimum(1, t / 0.6) * np.exp(-t / 2.2)
        sig = chord_pad(OUTRO, n, 2000, 0.8) * env[:, None]
        sub = np.sin(2 * np.pi * hz(29) * t) * env * 0.5
        add(self.pad, sig + pan(sub, 0), at(a), 0.42)
        add(self.verb, sig, at(a), 0.5)

    # hits ---------------------------------------------------------------------------------

    def event(self, ev: dict) -> None:
        name, pos = ev["name"], at(ev["bar"], ev["beat"])
        if name == "chime":
            for i, midi in enumerate((86, 81)):  # D6 then A5
                sig = self.note(bell, midi)
                add(self.fx, pan(sig, 0.15 * (1 - 2 * i)), pos + i * int(0.14 * SR), 0.3)
                add(self.delay, sig, pos + i * int(0.14 * SR), 0.12)
                add(self.verb, sig, pos + i * int(0.14 * SR), 0.25)
        elif name == "notifExpand":
            sig = self.note(bell, 81)
            add(self.fx, sig, pos, 0.17)
            add(self.verb, sig, pos, 0.2)
        elif name.startswith("hop"):
            for k in range(ev.get("nodes", 1)):  # one tick per node, a quick arpeggio
                sig = self.note(tick, TICKS[k % len(TICKS)])
                p = pos + int(k * 0.07 * SR)
                add(self.fx, pan(sig, -0.4 + 0.2 * k), p, 0.12)
                add(self.delay, sig, p, 0.05)
        elif name == "impact":
            sig = impact()
            self.impact[pos : pos + len(sig)] += sig[: self.n - pos]
            add(self.fx, sig, pos, 0.95)
            add(self.verb, sig, pos, 0.55)
        elif name.startswith("tour") or name == "explorer":
            sig = whoosh()
            start = pos - int(0.38 * SR)
            add(self.fx, sig, start, 0.2 if name == "explorer" else 0.26)
            add(self.verb, sig, start, 0.1)
        elif name.startswith("card"):
            i = int(name[-1]) - 1
            for midi in PROGRESSION[i % 4][2:]:
                add(self.fx, self.note(pluck, midi + 12), pos, 0.11)
            add(self.verb, self.note(pluck, PROGRESSION[i % 4][2] + 12), pos, 0.15)
            t = secs(0.6)
            add(self.fx, np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.2), pos, 0.3)
        elif name.startswith("member"):
            sig = self.note(pluck, TEAM[int(name[-1]) - 1])
            add(self.fx, sig, pos, 0.16)
            add(self.verb, sig, pos, 0.18)
            add(self.delay, sig, pos, 0.05)
        elif name.startswith("recoveryStep") or name == "recoveryReport":
            i = 4 if name == "recoveryReport" else int(name[-1]) - 1
            sig = self.note(blip, STEPS[i])
            add(self.fx, sig, pos, 0.1)
            add(self.delay, sig, pos, 0.04)
        elif name == "whatToDoClick":
            add(self.fx, ui_click(), pos, 0.35)

    # mix ----------------------------------------------------------------------------------

    def render(self) -> tuple[np.ndarray, np.ndarray]:
        for part in self.cut["music"]:
            self.part(part["part"], part["from"], part["to"])
        for ev in self.cut["events"]:
            self.event(ev)

        # sidechain: pad and bass dip under every kick (5 ms down, ~180 ms back)
        duck = np.zeros(self.n)
        shape = np.minimum(1, np.arange(int(0.4 * SR)) / (0.005 * SR)) * np.exp(
            -np.arange(int(0.4 * SR)) / (0.18 * SR)
        )
        for k in self.kicks:
            end = min(self.n, k + len(shape))
            duck[k:end] = np.maximum(duck[k:end], shape[: end - k])
        self.pad *= (1 - 0.35 * duck)[:, None]
        self.bass *= (1 - 0.55 * duck)[:, None]

        mix = self.drums + self.pad + self.bass + self.fx
        mix += 0.55 * reverb(self.verb) + 0.6 * echo(self.delay)
        mix = np.stack([highpass(mix[:, 0], 25), highpass(mix[:, 1], 25)], axis=1)

        for part in self.cut["music"]:  # hard cut to silence, with a 3 ms fade so it doesn't click
            if part["part"] == "silence":
                s, e = at(part["from"]), at(part["to"] + 1)
                fade = int(0.003 * SR)
                mix[s - fade : s] *= np.linspace(1, 0, fade)[:, None]
                mix[s:e] = 0
        tail = int(1.2 * SR)  # ring out to silence on the last sample
        mix[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 2

        loud = np.percentile(np.abs(mix), 99.9)
        mix *= 0.75 / loud  # the loudest parts sit near -2.5 dBFS before the limiter
        return limit(mix), self.impact


def limit(x: np.ndarray, lookahead: float = 0.003, release: float = 0.08) -> np.ndarray:
    """Lookahead peak limiter to the -1 dBFS ceiling, then exact peak normalization."""
    env = np.abs(x).max(axis=1)
    w = 1
    while w < lookahead * SR:  # env[i] = max of the next 2w samples
        env[:-w] = np.maximum(env[:-w], env[w:])
        w *= 2
    target = np.minimum(1.0, CEILING / np.maximum(env, 1e-9)).tolist()
    r = np.exp(-1 / (release * SR))
    gain, g = [], 1.0
    for v in target:
        g = v if v < g else v + (g - v) * r
        gain.append(g)
    y = x * np.array(gain)[:, None]
    return y * (CEILING / np.abs(y).max())


def write(path: Path, x: np.ndarray) -> None:
    pcm = np.round(x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def main() -> int:
    public = TRAILER / "public"
    public.mkdir(exist_ok=True)
    for key, cut in T["cuts"].items():
        mix, stem = Score(cut).render()
        n = cut["bars"] * BAR
        assert len(mix) == n, f"{key}: {len(mix)} samples, expected {n}"
        assert n * T["fps"] == cut["frames"] * SR, f"{key}: audio and video lengths differ"
        hit = next(e for e in cut["events"] if e["name"] == "impact")
        onset = int(np.flatnonzero(stem)[0])
        assert onset == at(hit["bar"], hit["beat"]), f"{key}: impact at {onset}"
        quiet = next(p for p in cut["music"] if p["part"] == "silence")
        assert not mix[at(quiet["from"]) : at(quiet["to"] + 1)].any(), (
            f"{key}: silence is not silent"
        )
        peak = 20 * np.log10(np.abs(mix).max())
        assert abs(peak + 1) < 0.01, f"{key}: peak {peak:.2f} dBFS"
        write(public / cut["audio"], mix)
        rms = {
            p["part"]: 20
            * np.log10(np.sqrt(np.mean(mix[at(p["from"]) : at(p["to"] + 1)] ** 2)) + 1e-12)
            for p in cut["music"]
        }
        print(
            f"{cut['audio']}: {len(mix) / SR:.3f} s, peak {peak:.2f} dBFS, "
            f"impact at sample {onset} = bar {hit['bar']} beat {hit['beat']} ({onset / SR:.3f} s)"
        )
        print("  rms dBFS: " + ", ".join(f"{k} {v:.1f}" for k, v in rms.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
