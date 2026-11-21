---
id: T-019
objective: O-1
status: review
owner: nico/claude
branch: t/T-019-frontend-integration
depends_on: [T-016, T-017, T-018]
scope: [src/ixh26/app/static/app.css, src/ixh26/app/templates/, src/ixh26/app/views/, src/ixh26/app/web.py, tests/app/test_frontend_pages.py, tests/app/test_web.py, README.md, docs/, tasks/]
contracts_used: []
policy: "1.1"
---
## Objective
Merge the detector-thresholds branch (daniele's T-018) with the network and verification branches, make the greys a little darker with more steps, and give the three backend features a web UI.
## Acceptance criteria
- [x] Detection settings page for analysts: four groups, units, field errors, 409 conflict, restore defaults, "Live data unavailable" on the two market sections
- [x] Find transaction page with a Mainnet or Testnet selector that leaves monitoring unchanged
- [x] Verify ownership page on each wallet: challenge, confirm, pending, expired, unavailable
- [x] Darker palette with five grey steps; muted text stays above 4.8:1
- [x] make check and make smoke green; pages exercised in the browser
## Out of scope
Requiring verification before watching a wallet; Mainnet-specific UI beyond the lookup.
## Log
- 11:25 nico/claude: policy 1.1 acknowledged. Base: master 212f8d4 (T-016, T-017 and the UI work already in) plus origin/t/T-018-detector-thresholds f327ea0. One README conflict, resolved by keeping both claim rows. The two backend tasks both use the id T-018 (mine, now merged, and daniele's); this one is T-019. No JavaScript added: addresses and tags are click-to-select instead of copy buttons, because section 4 needs a decision entry before any hand-written JS.
## Evidence
- make check: 121 passed; make smoke ok
- tests/app/test_frontend_pages.py: settings (analyst only, save and reload, restore, field errors, version conflict), lookup (selected network, failed results, 404/409/422/502), verification (pending, confirmed, expired, another user, unavailable)
- Browser run against the docker stack: settings with a 422, user home and wallet pages, verify page, live Mainnet lookup (404 for a made-up hash)
