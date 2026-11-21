# Trailer prompt: Ripple Guardian (66 s, 16:9)

Prompt for generating the demo trailer.

Notes before using it:

- **Fully animated.** No live footage, no screen recordings, no filmed people. Every frame is animated motion graphics: the app UI, the phone, the graph and the explorer are all redrawn as clean vector animation.
- **Recommended tool:** code-driven motion graphics (Remotion, After Effects, Rive, or an HTML/GSAP page rendered at 60 fps). Text-to-video models (Sora, Veo, Runway) garble text and numbers: use them only for the cold open, never for the graph or the notifications.
- **Music:** every cut and every animation lands on the beat of a 120 BPM track (1 beat = 0.5 s, 1 bar = 2 s, 33 bars in total). The scene timings below are already aligned to bars. Use a licensed or royalty-free track and list it in `THIRD_PARTY.md` (CLAUDE.md §7).
- **Numbers:** all taken from run 2 in `docs/E2E.md`, the run `make demo` produces today. The trailer must match what the live demo shows.
- **Name:** the product is Ripple Guardian.
- **Screenshots:** the real screens are in `artifacts/screenshots/`. Give them to the tool as a visual reference so the animated UI matches the demo.
- **SIMULATED:** Exchange and Exchange B are Testnet wallets we control. The "SIMULATED" label stays visible on the graph, as in the app (CLAUDE.md §8).
- **Verified values:** the app prints XRP with 6 decimals (`flows/trace_report.py::value_text`), so the notification reads 54.939982 XRP, as in `artifacts/screenshots/analyst-hop-graph.png`. Hash `7758D5E4…` was checked on Testnet: tag 777001, 25.107992 XRP delivered, `tesSUCCESS`, destination `rQs8mJ…gqNG`. It is the first of the three deposits to that tag, which is the link the notification opens.
- **Positioning:** "blockchain forensics framework" is the category keyword. It appears in the subtitle, the lower third of the trace scene and the end card.
- **Team photos:** the end card uses animated initials avatars. If the team provides portraits, swap them in as flat illustrated avatars to keep the trailer fully animated.

---

## Prompt

```text
Create a 66-second, 16:9 (1920x1080, 60 fps), fully animated product trailer for
"Ripple Guardian", a blockchain forensics framework for the XRP Ledger: wallet
protection and theft tracing, built at the IXH26 Italian XRPL Hackathon. All on-screen text, voice and labels are in English.
Audience: a hackathon jury judging Innovation, Execution, Impact and Pitch.
Goal: in one minute, a judge understands the problem, sees every feature working,
and remembers the closing line.

FORMAT
- 100% animated motion graphics. No live-action footage, no screen recordings,
  no real people. The app UI, the phone, the hop graph and the explorer page are
  all rebuilt as crisp flat vector animation that matches the reference screenshots.
- No voice-over. The story is told by on-screen text and the music.

STYLE
- Clean, premium motion design in the spirit of a high-end product launch film.
  Flat UI, no 3D, no glitch effects, no hacker clichés
  (no hoodies, no green matrix code, no padlocks).
- Dark background #0b1220. Text #ffffff and #e1e8ef. Danger red #b4233a
  (glow #a3192f). Trust blue #5ea2f5 (secondary #4a9be0). Nothing else.
- One typeface: Inter. Headlines semibold 72-96 px, UI text 28-36 px,
  JetBrains Mono only for addresses, tags and tx hashes.
- Motion: ease-out cubic-bezier(0.16, 1, 0.3, 1), 400-700 ms per move.
  Elements enter with a 12 px rise and fade, staggered on eighth notes (250 ms).
  One idea on screen at a time. Every text stays readable for at least 1.5 s.
  Camera moves are slow push-ins and pans across the UI, never shaky.

SOUNDTRACK (beat-synced)
- Original-sounding modern electronic score, 120 BPM, 4/4, minor key,
  tense but clean: soft pulse, warm sub bass, crisp percussion, no vocals.
- 1 beat = 0.5 s, 1 bar = 2 s, 33 bars in total. Every scene cut lands on a downbeat.
  Every text line, node and card appears on a beat or an eighth note.
- Structure:
  Bars 1-3   (0:00-0:06)  near silence, one notification chime on beat 1,
                          a low drone fades in.
  Bars 4-6   (0:06-0:12)  heartbeat kick on beats 1 and 3; each problem line
                          lands on a kick.
  Bars 7-10  (0:12-0:20)  hi-hats enter, tension rises; the red band pulses
                          in time with the kick.
  Bars 11-13 (0:20-0:26)  a soft riser; each recovery checkbox ticks on a beat.
  Bars 14-20 (0:26-0:40)  THE DROP: full beat. One graph hop per bar, a subtle
                          tick for every node. Bar 20, beat 1: a deep impact hit
                          as tag 777001 turns red.
  Bars 21-23 (0:40-0:46)  beat thins out, the notification lands on a downbeat.
  Bars 24-27 (0:46-0:54)  confident groove, one card per bar.
  Bars 28-30 (0:54-1:00)  music cuts to silence on bar 28 beat 1. Logo appears
                          in silence; one final sustained chord under the
                          closing line.
  Bars 31-33 (1:00-1:06)  the chord resolves into a soft, warm outro loop;
                          each team member card lands on a beat, then the
                          music rings out to silence.

ON-SCREEN TEXT MUST BE EXACT. Do not invent numbers, names or UI labels.

SCENE 1 - COLD OPEN (0:00-0:06, bars 1-3)
Black screen. Notification chime. An animated phone lock-screen notification
slides in, centered:
  "3:12 AM  ·  Ripple Guardian"
  "Signing key changed"
Hold. Then a line types under it in white: "Your seed just leaked."

SCENE 2 - THE PROBLEM (0:06-0:12, bars 4-6)
Three short lines, one per kick, left aligned, large:
  "A new key is added."
  "The wallet is drained."
  "The XRP is on an exchange in minutes."
Then, in red: "Most owners find out in the morning."

SCENE 3 - THE ALERT (0:12-0:20, bars 7-10)
Cut to the animated app (dark UI). Tight shot on the wallet card: its status band
turns red and pulses with the kick. Alert feed entries slide in, newest first:
  "Signing key changed"
  "Outgoing payment: 99.99997 XRP"
A red button "What to do" glows once and an animated cursor clicks it.

SCENE 4 - RECOVERY (0:20-0:26, bars 11-13)
Screen title: "What to do now". Four numbered steps stagger in; each checkbox
ticks on a beat:
  1 Lock it down
  2 Save what's left
  3 Find the money
  4 Report it
Step 4 shows a PDF icon labelled "Incident report · SHA-256 fingerprint".

SCENE 5 - THE TRACE (0:26-0:40, bars 14-20)  <- hero shot, give it the most care
Switch to the analyst view. Caption top-left: "Analyst · Taint trace".
On the drop, a hop graph draws itself left to right, one hop per bar, link width
proportional to value, a small XRP amount riding each link as it draws.
Column headers: "Victim", "Hop 1", "Hop 2", "Hop 3", "Hop 4".
Each node shows a short address and its tainted amount, exactly as in the app:
  Victim:  "Victim"            "99.99997 XRP (100%)"
  Hop 1:   "rhHc1P…9Uew"       "99.99997 XRP (100%)"   (the attacker)
  Hop 2:   "rNYg2Q…URvi"       "59.339982 XRP (59%)"
           "rKBgDa…pC6z"       "39.559988 XRP (40%)"
  Hop 3:   "rUNGZv…Upti"       "26.207992 XRP (26%)"
           "rD5qcB…wkFq"       "23.075993 XRP (23%)"
           "rfAm7G…VUH9"       "20.383994 XRP (20%)"
           "rPm7F5…ieAr"       "15.383995 XRP (15%)"   (red: keeps its share)
           "rEDHuU…uayN"       "11.647996 XRP (12%)"
  Hop 4:   "Exchange (SIMULATED), tag 777001"    "54.939982 XRP (55%)"
           "Exchange B (SIMULATED), tag 4242"    "21.975993 XRP (22%)"
On the impact hit (bar 20, beat 1): the "Exchange (SIMULATED), tag 777001" node
fills red and scales up slightly, with a glowing ring.
Lower third: "Blockchain forensics · 12 tainted transfers · 4 hops ·
every amount from delivered_amount".
Then the cursor hovers one mule: everything off its money path dims to 20%.

SCENE 6 - THE OWNER KNOWS (0:40-0:46, bars 21-23)
Back to the animated phone. A critical notification slides in on the downbeat:
  "Stolen funds located"
  "Traced 54.939982 XRP of your stolen funds to Exchange (SIMULATED) (rQs8mJ…gqNG)
   with destination tag 777001. Share this with the exchange and the police."
The cursor taps "View on XRPL Testnet explorer". An animated browser window opens
on testnet.xrpl.org showing transaction hash "7758D5E4…", destination tag
"777001", delivered "25.107992 XRP" and a green "tesSUCCESS".

SCENE 7 - WHY XRPL (0:46-0:54, bars 24-27)
Four cards in a 2x2 grid, one per bar, blue icon + one line each:
  "delivered_amount: amounts that cannot be faked"
  "Destination tag: the customer, not just the exchange"
  "7 of 7 traced transfers match the ledger"
  "Public flags, signed with the analyst's name"

SCENE 8 - CLOSE (0:54-1:00, bars 28-30)
Music cuts to silence. Everything fades to #0b1220. The Ripple Guardian logo
fades in, centered. Under it, small caps in trust blue:
  "BLOCKCHAIN FORENSICS FRAMEWORK FOR THE XRP LEDGER"
On the final chord, under it, white, semibold:
  "Know the moment your wallet moves."

SCENE 9 - TEAM END CARD (1:00-1:06, bars 31-33)
The logo shrinks and glides to the top center. A clean, centered credits layout
builds on the beat:
  Line 1 (white, semibold, large): "Ripple Guardian"
  Line 2 (blue): "by Team CyberGuys"
Six member cards in one row (two rows of three on narrow layouts), each a round
animated avatar with initials, the full name and the handle in monospace,
landing one per beat, left to right:
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
Hold, then fade to black as the music rings out.

DO NOT
- use live-action footage, screen recordings or real people;
- use any language other than English;
- show seeds, private keys or real personal data;
- write "mainnet", "live on mainnet" or any claim beyond the text above;
- add extra features, logos of real exchanges, or partner brands;
- use em dashes in on-screen text.
```

---

## Short cut (30 s)

For social media or a tight 3-minute pitch: keep scenes 1, 3, 5, 6, 8 and 9, at 120 BPM: 0:00-0:04 (bars 1-2), 0:04-0:08 (bars 3-4), 0:08-0:18 (bars 5-9, one hop per bar, impact on bar 9), 0:18-0:22 (bars 10-11), 0:22-0:26 (bars 12-13, silence then final chord), 0:26-0:30 (bars 14-15, team end card with all six names).

## References

- Numbers and hashes: `docs/E2E.md` (run 2), claim and evidence table in `README.md`.
- Notification text: `src/ixh26/core/alerts.py`, `src/ixh26/app/views/common.py`.
- Recovery steps: `src/ixh26/app/templates/user/recover.html`.
- Logo: `docs/assets/logo.jpeg`.
- Team: `README.md` (Team section). Event, track and venue: hackathon platform, event `ixh26-italian-xrpl-hackathon-4b11386b`.
