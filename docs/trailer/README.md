# Ripple Guardian trailer

A 90-second trailer and a 30-second cut, made from real captures of the running app, an original soundtrack synthesized in Python, and a Remotion edit. [BRIEF.md](BRIEF.md) is the creative brief and [START_PROMPT.md](START_PROMPT.md) is the prompt the build started from.

| Path | What it is |
|---|---|
| `capture.py` | Signs in to the running app, saves 2x screenshots, browser recordings, the server's HTML of each page, and `public/captures/manifest.json` with the values on screen and the box of every key element |
| `timing.json` | Bars, beats, scenes and every sync event, for both cuts. The music and the video both read it |
| `audio/make_music.py` | The soundtrack, numpy only. Writes `public/music.wav` and `public/music-30s.wav` |
| `src/` | The Remotion project: one component per scene in `src/scenes/`, shared pieces in `src/components/` |

The renders are in `out/` (`trailer.mp4`, `trailer-30s.mp4`, the `tmp-preview-full.mp4` work preview and the `stills/` frames), and the captures and music they were built from are in `public/`. Run the three steps below only to rebuild them.

## 1. Capture

The app runs on one machine and is exposed with ngrok; the capture runs on another. On the app machine, follow [START_PROMPT.md](START_PROMPT.md) up to `ngrok http 8000`. Then, on this machine, from the repo root:

```bash
export TRAILER_BASE_URL='https://xxxx.ngrok-free.app'
export TRAILER_USER='alice:PASSWORD' TRAILER_ANALYST='analyst:PASSWORD'
uv run --with playwright playwright install chromium-headless-shell
uv run --with playwright python docs/trailer/capture.py
```

The run takes a minute or two. It stops with a message if the app is down, a login fails, the trace isn't finished or alice has no "Stolen funds located" alert. Once it prints `app captures done: the tunnel can close`, the app machine can shut down.

The testnet.xrpl.org screenshot needs only the public explorer:

```bash
uv run --with playwright python docs/trailer/capture.py --explorer-only
```

What the script does on top of opening pages:

- It only reads from the app and submits no form.
- Headless Chromium draws no pointer, so it injects one that follows the real mouse events, and moves the mouse along eased paths.
- The trace recording is retimed while it is captured. An injected style sets the delay between hops to 2 s (one bar) instead of the app's 450 ms, the value particles start once their link is drawn, and each arrowhead waits for its link. Pops, draws and the rest of the page are the app's own.
- On WSL it copies Segoe UI and Consolas from `C:\Windows\Fonts` into a temporary fontconfig folder, so the screens look as they do on Windows. Elsewhere the browser's default fonts are used.
- `public/captures/site/` keeps the server's HTML of every captured page and its static files. After the tunnel is gone, `python3 -m http.server -d docs/trailer/public/captures/site 8000` serves them again for a browser or a one-off Playwright script. There is no backend behind that copy, so `capture.py` itself still needs the live app.

## 2. Music

```bash
uv run --with numpy python docs/trailer/audio/make_music.py
```

It takes about 20 seconds and checks its own output: 90.000 s and 30.000 s exactly, peak at -1 dBFS, the impact on the exact sample of bar 20 beat 1 (bar 9 in the short cut), and digital silence through bar 40 (bar 12). Everything is synthesized: oscillators, envelopes, one-pole filters, a feedback delay and a small Schroeder reverb.

## 3. Video

```bash
cd docs/trailer
npm install
npm run render       # out/trailer.mp4, about 6 minutes on a 16-thread laptop
npm run render:30    # out/trailer-30s.mp4, about 2 minutes
```

The first render downloads Chrome Headless Shell. On a machine with less than 8 GB of RAM, add `-- --concurrency=4` to the render command. On WSL, a render can stop with `net::ERR_NETWORK_CHANGED` when the host's network changes; running it again is enough.

To preview, or to check one frame:

```bash
npx remotion studio
npx remotion still src/index.ts Trailer out/still.png --frame=2280
```

## Timing

120 BPM at 60 fps: a beat is 30 frames, a bar 120 frames, and 45 bars make 5400 frames. Bars and beats in `timing.json` count from 1, so bar 20 beat 1 (the impact on tag 777001) is frame 2280, 38.000 s, sample 1,824,000. Every scene starts on a downbeat and every caption, node and card appears on a beat or an eighth note.

In the trace, the recording plays at normal speed. `LAG` in `src/scenes/Trace.tsx` shifts it by 3 frames so that the exchange tooltip opens on the impact.

## Numbers on screen

The values come from the run captured on 21 Nov 2026, and `capture.py` reads them back from the app into `manifest.json`:

- 98.899979 XRP stolen; trace 1 has 12 tainted transfers over 4 hops
- Exchange (SIMULATED), `rPfXCA…HMtw`, tag 777001: 54.279986 XRP (55%)
- Exchange B (SIMULATED), `rnF3cd…9NDN`, tag 4242: 21.711995 XRP (22%)
- one mule keeps 15.207997 XRP (15%)
- first deposit to tag 777001: `62E75B3A…`, `tesSUCCESS` on Testnet, 24.810994 XRP delivered

"7 of 7 traced transfers match the ledger" comes from run 1 in [docs/E2E.md](../E2E.md).

## Credits

| Component | Licence | Used for |
|---|---|---|
| [Remotion](https://www.remotion.dev) 4.0.545 (`remotion`, `@remotion/cli`, `@remotion/google-fonts`) | [Remotion License](https://www.remotion.dev/license): free for individuals and for companies of up to 3 people | Editing and rendering |
| [React](https://react.dev) 19 | MIT | Remotion components |
| [Playwright for Python](https://playwright.dev/python/) 1.65 | Apache-2.0 | `capture.py` |
| [NumPy](https://numpy.org) | BSD-3-Clause | `audio/make_music.py` |
| [Inter](https://rsms.me/inter/) | SIL OFL 1.1 | Captions and titles |
| [JetBrains Mono](https://www.jetbrains.com/lp/mono/) | SIL OFL 1.1 | Handles and `delivered_amount` |
| [Lucide](https://lucide.dev) icons: shield-check, tag, circle-check, flag | ISC | Why XRPL cards |
| Segoe UI, Consolas | Windows system fonts, not distributed | Rendering the app's own font stack in the captures |
| Music | Original, generated by `audio/make_music.py` | Soundtrack |

The logo and the app's icon are the team's own (`docs/assets/logo.jpeg`, `src/ixh26/app/static/logo-mark.png`).
