---
id: T-008
objective: O-1
status: review
owner: nico/claude
branch: t/T-008-web-ui
depends_on: [T-003, T-004]
scope: [src/ixh26/app/web.py, src/ixh26/app/templates/, src/ixh26/app/static/, tests/app/test_web.py, THIRD_PARTY.md]
contracts_used: [Alert, TraceResult, AccountLabel]
policy: "1.0"
---
## Objective
One web app, two roles: users see only their wallets, statements, in-app notifications and analyst flags; analysts see detector findings, run traces and flag accounts/txs.
## Acceptance criteria
- [x] Server-rendered pages (Jinja2 + HTMX), one CSS file with design tokens, reusable macros; animation hooks ready but no animations yet
- [x] User pages: dashboard, wallet detail (history + statement), notifications (live polling, mark read, per-wallet settings), flag lookup
- [x] Analyst pages: findings queue (flag / dismiss), traces (start + view), flags (create / revoke)
- [x] Role enforcement tested: a user gets 403 on analyst pages
- [x] No personal data collected: username + password only
## Out of scope
Animations, email, Clawback/Freeze, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
- 00:35 nico/claude: app/web.py + templates + static/app.css (tokens, components, motion hooks: --motion-*, data-anim, htmx swap classes, reduced-motion zeroes durations). Design: cool ledger-paper, ink navy, semantic red/amber/green only for state; serif display. Signature element: the taint ribbon on the trace page. CSRF relies on SameSite=Lax cookies; cookie not Secure (localhost demo).
## Evidence
- tests/app/test_web.py: login redirect, register + watch wallet, user pages + 403 on analyst pages, analyst findings/trace ribbon/flag visible to a user
- Screenshots of SIMULATED data reviewed locally (home, wallet, findings, trace, login)
