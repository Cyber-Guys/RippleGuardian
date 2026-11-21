# Start prompt: build the trailer

Open a fresh Claude Code session in the repo root (`cd ~/xrpl_hackathon && claude`) and paste the block below. The session reads [BRIEF.md](BRIEF.md), runs the app locally, captures the real screens, synthesizes the music and renders the video. Everything lives in `docs/trailer/`.

Before starting:

- Docker running, `make setup` done, a `JWT_SECRET` in `.env`.
- Have the passwords for the local demo users `alice` and `analyst` ready, or let the session ask you to create them. The session never writes passwords to files.

```text
Build the Ripple Guardian trailer described in docs/trailer/BRIEF.md.

AUTHORIZATION AND LIMITS
- A human on the team authorized this work outside the task system. Work only inside
  docs/trailer/. JavaScript/TypeScript is allowed there for Remotion only.
- Do not modify src/, scripts/, tests/, pyproject.toml, uv.lock, Makefile or CLAUDE.md.
  Follow CLAUDE.md for everything else: never open, print or grep .env or any seed,
  never commit secrets, no AI attribution in commits.
- Create docs/trailer/.gitignore for node_modules/, out/, captures/ and *.wav.
  Commit only sources (scripts, Remotion code, timing.json, docs). Never commit
  binaries over 5 MB.
- If something blocks you (Testnet down, missing users, Docker errors), stop and
  ask me instead of working around it.

STEP 1 - READ
- Read docs/trailer/BRIEF.md fully. The ```text block is the creative brief: follow
  every scene, timing, exact caption, color and font. Read README.md (Quickstart),
  docs/E2E.md and scripts/e2e_browser.py.

STEP 2 - RUN THE PLATFORM LOCALLY
- Check whether the stack is already up with demo data: curl
  http://localhost:8000/healthz and look for an existing trace. If it is, reuse it.
- Otherwise follow the README Quickstart: docker compose up -d --build, create the
  users alice and analyst (role analyst), then run make demo with
  ARGS="--watch-user alice --auto-trace analyst" and the DATABASE_URL from the
  README. On WSL prefix network commands with RES_OPTIONS="timeout:1 attempts:1".
  Wait until the trace has finished and alice has the "Stolen funds located"
  notification.
- Write down the real values the app now shows (addresses, amounts, trace id,
  deposit hash). If they differ from the brief, the captions follow the app.

STEP 3 - CAPTURE THE REAL SCREENS (docs/trailer/capture.py)
- Python + Playwright via: uv run --with playwright python docs/trailer/capture.py
  Reuse the login and page flow of scripts/e2e_browser.py. Read credentials from
  the TRAILER_USER and TRAILER_ANALYST environment variables (name:password),
  which I will set; never hard-code them.
- Viewport 1920x1080, device_scale_factor 2, Chromium headless, no browser chrome.
- Screenshots (full viewport, after the entrance motion settles) for every page in
  scenes 3, 4, 6 and 7 of the brief, plus the testnet.xrpl.org page of the deposit
  transaction.
- Browser recordings (record_video, 1920x1080) for the interactive moments:
  the cursor moving to and clicking "What to do"; the hop graph drawing itself on
  /analyst/traces/{id} and then the hover on a mule; expanding the
  "Stolen funds located" notification. Move the mouse in smooth, eased paths
  (many small page.mouse.move steps), never teleport.
- Save to docs/trailer/public/captures/ with clear names, and write
  docs/trailer/public/captures/manifest.json listing each file, its page and the
  pixel box of the key element (from element.bounding_box()) so Remotion can zoom
  and spotlight exactly on it.
- Open a few captures yourself and check: real data visible, nothing secret,
  no error page, text sharp.

STEP 4 - SHARED TIMING
- docs/trailer/timing.json is the single source of truth: fps 60, bpm 120,
  BEAT = 30 frames, BAR = 120 frames, 45 bars = 5400 frames (90 s), and every sync
  event from the brief as {name, bar, beat}: chime, problem lines, recovery
  highlights, each graph hop, the 777001 impact (bar 20 beat 1), each tour
  feature change, each Why XRPL card, silence at bar 40, final chord, each team
  card. The music script and every Remotion scene read it.

STEP 5 - SOUNDTRACK (docs/trailer/audio/make_music.py -> public/music.wav)
- Python 3 + numpy (uv run --with numpy), 48 kHz, 16-bit stereo, exactly 90.000 s.
- Synthesize everything: oscillators, ADSR envelopes, one-pole low-pass filter,
  feedback delay, short stereo reverb. Instruments: sine kick with click,
  filtered-noise hi-hats, sub bass, detuned saw pad (Dm - Bb - F - C), bell for the
  chime, noise riser, deep impact (sine drop + noise burst + reverb tail), short
  whoosh for tour transitions, ticks for graph nodes, sustained final chord.
- Follow the bar map in the brief exactly, reading event times from timing.json.
- Mix: peak -1 dBFS, gentle limiter, light sidechain of pad and bass to the kick,
  enough mids to sound good on laptop speakers.
- Print duration, peak level and the sample offset of the impact; assert it equals
  bar 20 beat 1 exactly.

STEP 6 - VIDEO (Remotion in docs/trailer/)
- Scaffold Remotion here (npx create-video@latest, blank, TypeScript).
- Composition 1920x1080, 60 fps, 5400 frames, <Audio src={staticFile("music.wav")}/>.
- One component per scene; every Sequence start and element entry derives from
  timing.json. Shared components: FloatingWindow (rounded browser frame, soft
  shadow, on the #0b1220 stage), CameraMove (eased scale and translate between two
  boxes from manifest.json), Spotlight (dims everything outside a box, plus a soft
  ring), Caption (blue eyebrow + white title, bottom-left), KineticLine.
- Recordings via <OffthreadVideo>, retimed with playbackRate or trimmed so the
  graph shows one hop per bar and the impact lands on bar 20 beat 1.
- Fonts: Inter and JetBrains Mono via @remotion/google-fonts.
- After each scene, render stills at its key frames (npx remotion still), look at
  them, and fix overlaps, blurry zooms or unreadable text before moving on.

STEP 7 - OUTPUT
- Render docs/trailer/out/trailer.mp4 (h264, crf 18, AAC 320k) and the 30-second
  cut from the brief as out/trailer-30s.mp4. Give me both paths.
- Write docs/trailer/README.md: how to rerun each step (make the commands copyable)
  and a credits list (Remotion, Playwright, numpy, fonts, with licenses; the music
  is original, generated by audio/make_music.py). Tell me which rows to add to
  THIRD_PARTY.md; do not edit it yourself.
- Commit the sources on a branch t/trailer with small commits, push the branch,
  and tell me. Do not merge into master.
- Do not change any text, number or name from the brief except to match what the
  running app really shows. Do not use em dashes.
```
