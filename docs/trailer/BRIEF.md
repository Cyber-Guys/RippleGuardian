# Trailer brief: Ripple Guardian (90 s, 16:9)

Creative brief for the demo trailer. The build instructions for a Claude Code session are in [START_PROMPT.md](START_PROMPT.md).

Notes:

- **Real product, animated.** Every product shot is the real Ripple Guardian app, running locally with the data from `make demo`, captured with a scripted browser and then animated in Remotion: floating browser windows, slow push-ins, zooms on the detail that matters, callouts and kinetic type. Only the cold open, the problem lines, the "Why XRPL" cards and the end cards are pure motion graphics. No filmed people.
- **Music:** original, synthesized in code by the build (`audio/make_music.py`), 120 BPM (1 beat = 0.5 s, 1 bar = 2 s, 45 bars). Every scene cut lands on a downbeat.
- **Numbers:** all from run 2 in `docs/E2E.md`, the run `make demo` produces today. If a fresh `make demo` run gives different addresses or amounts, the on-screen captions follow the fresh run, because the captured screens will show it.
- **Verified values (run 2):** the app prints XRP with 6 decimals (`flows/trace_report.py::value_text`), so the notification reads 54.939982 XRP. Hash `7758D5E4…` was checked on Testnet: tag 777001, 25.107992 XRP delivered, `tesSUCCESS`, destination `rQs8mJ…gqNG`. It is the first of the three deposits to that tag, which is the link the notification opens.
- **SIMULATED:** Exchange and Exchange B are Testnet wallets we control. The "SIMULATED" label stays visible, as in the app (CLAUDE.md §8).
- **Positioning:** "blockchain forensics framework" is the category keyword. It appears in the subtitle, the trace scene and the end card.

---

## Brief

```text
Create a 90-second, 16:9 (1920x1080, 60 fps) product trailer for "Ripple Guardian",
a blockchain forensics framework for the XRP Ledger: wallet protection and theft
tracing, built at the IXH26 Italian XRPL Hackathon. All on-screen text is in English.
Audience: a hackathon jury judging Idea, Execution, Pitch and Potential.
Goal: a judge understands the problem in 10 seconds, watches the real product catch,
trace and explain a real Testnet theft, sees every feature of the platform, and
remembers the closing line.

FORMAT
- Product shots are real captures of the running app (screenshots and short browser
  recordings at 1920x1080, device scale factor 2). They are animated, never shown as
  a flat static slide: each capture sits in a floating browser window with soft
  shadow and rounded corners on the dark stage, with slow push-ins, pans, zooms to
  the key element, a highlight ring or spotlight on what matters, and short captions.
- Pure motion graphics only for: cold open, problem lines, Why XRPL, close, team card.
- No voice-over. The story is told by captions, the real UI and the music.

STYLE
- Premium product launch film. Flat, calm, precise. No 3D, no glitch effects,
  no hacker clichés (no hoodies, no matrix code, no padlocks).
- Stage background #0b1220. The app itself is light; it floats on the dark stage.
  Text #ffffff and #e1e8ef. Danger red #b4233a (glow #a3192f). Trust blue #5ea2f5
  (secondary #4a9be0). Nothing else.
- Inter for all captions (headlines semibold 72-96 px, captions 32-40 px),
  JetBrains Mono for addresses, tags and hashes.
- Motion: ease-out cubic-bezier(0.16, 1, 0.3, 1), 400-700 ms per move. Captions
  enter with a 12 px rise and fade, staggered on eighth notes (250 ms). One idea on
  screen at a time. Every caption stays readable for at least 1.5 s. Zooms never
  exceed 2.2x, and text in a zoomed capture must stay sharp.
- Feature captions: a small blue eyebrow (the area, e.g. "OWNER" or "ANALYST") and
  a white title line, bottom-left, consistent across the whole film.

SOUNDTRACK (original, synthesized, beat-synced)
- Modern electronic score, 120 BPM, 4/4, D minor, tense but clean: soft pulse, warm
  sub bass, crisp percussion, no vocals.
- 1 beat = 0.5 s, 1 bar = 2 s, 45 bars. Every scene cut lands on a downbeat; every
  caption, node and card appears on a beat or an eighth note.
- Structure:
  Bars 1-3   (0:00-0:06)  near silence, one notification chime on beat 1, low drone.
  Bars 4-6   (0:06-0:12)  heartbeat kick on beats 1 and 3; each problem line lands
                          on a kick.
  Bars 7-10  (0:12-0:20)  hi-hats enter, tension rises; the red status pulses with
                          the kick.
  Bars 11-13 (0:20-0:26)  soft riser; each recovery step highlight lands on a beat.
  Bars 14-20 (0:26-0:40)  THE DROP: full beat. One graph hop per bar, a subtle tick
                          per node. Bar 20 beat 1: deep impact hit on tag 777001.
  Bars 21-23 (0:40-0:46)  beat thins out; the notification lands on a downbeat.
  Bars 24-35 (0:46-1:10)  confident groove for the platform tour; a short whoosh
                          on every feature change (every 2 bars).
  Bars 36-39 (1:10-1:18)  build, one card per bar.
  Bars 40-42 (1:18-1:24)  hard cut to silence on bar 40 beat 1. Logo in silence;
                          one sustained final chord under the closing line.
  Bars 43-45 (1:24-1:30)  the chord resolves into a warm outro; each team card
                          lands on a beat; ring out to silence.

ON-SCREEN TEXT MUST BE EXACT. Do not invent numbers, names or UI labels. Captions
quote the real UI.

SCENE 1 - COLD OPEN (0:00-0:06, bars 1-3) - motion graphics
Black. Chime. A phone lock-screen notification slides in, centered:
  "3:12 AM  ·  Ripple Guardian"
  "Signing key changed"
A line types under it: "Your seed just leaked."

SCENE 2 - THE PROBLEM (0:06-0:12, bars 4-6) - motion graphics
One line per kick, left aligned, large:
  "A new key is added."
  "The wallet is drained."
  "The XRP is on an exchange in minutes."
Then, in red: "Most owners find out in the morning."

SCENE 3 - THE ALERT (0:12-0:20, bars 7-10) - real UI, owner "alice"
Capture: the owner dashboard and the wallet page in the compromised state.
Push in on the red status and the alert feed ("Signing key changed",
"XRP sent"). Spotlight the red "What to do" button; the recorded cursor clicks it.
Caption: eyebrow "OWNER", title "Alerts in plain words, the moment something happens."

SCENE 4 - RECOVERY (0:20-0:26, bars 11-13) - real UI
Capture: /wallets/{address}/recover. Pan down the four steps
("Lock it down", "Save what's left", "Find the money", "Report it"), one highlight
per beat, ending on the "Report" PDF download.
Caption: "A four-step recovery plan and a PDF incident report with a SHA-256
fingerprint."

SCENE 5 - THE TRACE (0:26-0:40, bars 14-20) - real UI, analyst  <- hero shot
Capture: a browser recording of /analyst/traces/{id} while the hop graph draws
itself, then hovering a mule so everything off its money path dims.
Retime the recording so one hop appears per bar. Zoom from the victim to the
right edge as the graph grows. On bar 20 beat 1 (impact), spotlight the node
"Exchange (SIMULATED), tag 777001" and its "54.939982 XRP (55%)".
Captions, one after the other:
  eyebrow "ANALYST", title "Blockchain forensics: follow the money, hop by hop."
  "12 tainted transfers over 4 hops, every amount read from delivered_amount"

SCENE 6 - THE OWNER KNOWS (0:40-0:46, bars 21-23) - real UI
Capture: /notifications with the "Stolen funds located" entry expanded:
  "Traced 54.939982 XRP of your stolen funds to Exchange (SIMULATED) (rQs8mJ…gqNG)
   with destination tag 777001. Share this with the exchange and the police."
Then a capture of the same transaction on testnet.xrpl.org (hash 7758D5E4…,
destination tag 777001, tesSUCCESS) slides in over it.
Caption: "The exact destination tag: the customer account the exchange can freeze."

SCENE 7 - PLATFORM TOUR (0:46-1:10, bars 24-35) - real UI, 2 bars per feature
Fast, clean, consistent: each feature is one capture in the floating window, one
push-in to its key element, one caption. Whoosh + cut on every downbeat pair.
  Bars 24-25  /register             OWNER    "Sign up with just a username: no email or phone number needed."
  Bars 26-27  /wallets              OWNER    "Watch any wallet, live from the ledger."
  Bars 28-29  /wallets/{a}/verify   OWNER    "Prove you own it with a one-drop payment."
  Bars 30-31  /analyst/findings     ANALYST  "Four detectors raise findings to review."
  Bars 32-33  /flags                ANALYST  "Flags signed with the analyst's name,
                                              checked by every user before paying."
  Bar  34     /analyst/settings     ANALYST  "Tune every detector rule."
  Bar  35     /transactions/{hash}  ANALYST  "Look up any validated transaction."

SCENE 8 - WHY XRPL (1:10-1:18, bars 36-39) - motion graphics
Four cards in a 2x2 grid, one per bar, blue icon + one line each:
  "delivered_amount: partial payments can't inflate the amounts"
  "Destination tag: it points to one customer's account at the exchange"
  "7 of 7 traced transfers match the ledger"
  "Public flags, signed with the analyst's name"

SCENE 9 - CLOSE (1:18-1:24, bars 40-42) - motion graphics
Silence. Fade to #0b1220. The Ripple Guardian logo fades in, centered. Under it,
small caps in trust blue: "BLOCKCHAIN FORENSICS FRAMEWORK FOR THE XRP LEDGER".
On the final chord, white, semibold: "Know the moment your wallet moves."

SCENE 10 - TEAM END CARD (1:24-1:30, bars 43-45) - motion graphics
The logo glides to the top center. Centered credits build on the beat:
  "Ripple Guardian" (white, semibold, large)
  "by Team CyberGuys" (blue)
Six member cards in one row, round avatar with initials, full name, handle in
monospace, one per beat, left to right:
  "NG"  "Nicola Ghisu"      "NicoXVI"
  "TC"  "Tommaso Casti"     "t0mm1"
  "DO"  "Daniele Orrù"      "DenInDev"
  "AC"  "Andrea Cerolini"   "percyghost"
  "DO"  "Diego Oliva"       "doliv"
  "NM"  "Nicholas Meli"     "uNickz"
Bottom block, grey, three centered lines:
  "IXH26 Italian XRPL Hackathon"
  "Track: XRPL applications"
  "Department of Mathematics, University of Bari Aldo Moro · Bari, Italy · 20-21 November 2026"
Fade to black as the music rings out.

DO NOT
- show seeds, private keys, passwords, the .env file or real personal data;
- show browser chrome with personal bookmarks, other tabs or the local username;
- use any language other than English;
- write "mainnet", "live on mainnet" or any claim beyond the text above;
- add features that are not in the app, logos of real exchanges, or partner brands;
- use em dashes in on-screen text.
```

---

## Short cut (30 s)

Scenes 1, 3, 5, 6, 9 and 10 at 120 BPM: 0:00-0:04 (bars 1-2), 0:04-0:08 (bars 3-4), 0:08-0:18 (bars 5-9, one hop per bar, impact on bar 9), 0:18-0:22 (bars 10-11), 0:22-0:26 (bars 12-13, silence then final chord), 0:26-0:30 (bars 14-15, team card).

## References

- Numbers and hashes: `docs/E2E.md` (run 2), claim and evidence table in `README.md`.
- Notification text: `src/ixh26/core/alerts.py`, `src/ixh26/app/views/common.py`.
- Recovery steps: `src/ixh26/app/templates/user/recover.html`.
- Existing browser walkthrough to reuse for captures: `scripts/e2e_browser.py`.
- Logo: `docs/assets/logo.jpeg`.
- Team: `README.md` (Team section). Event, track and venue: hackathon platform, event `ixh26-italian-xrpl-hackathon-4b11386b`.
