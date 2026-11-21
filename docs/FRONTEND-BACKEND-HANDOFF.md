# Prompt for the frontend agent

You are implementing the UI for Ripple Guardian. Read `CLAUDE.md` and the relevant task files.
Use a separate frontend branch and worktree. Use the existing FastAPI, Jinja2 and HTMX stack.
Keep API contracts and detection logic as implemented.

Implement Section A for `t/T-018-detector-thresholds`. Sections B and C cover the previously
delivered network and wallet verification backend changes. Include them when those branches are
part of your integration base. Check the actual routes on your base before attaching controls.

## A. Analyst detector settings

Add a **Detection settings** page under the analyst navigation near Findings. The existing
entry points are `src/ixh26/app/templates/base.html`, `src/ixh26/app/views/analyst_pages.py`,
and `src/ixh26/app/views/common.py`. Use `PageAnalyst` for HTML routes. For server-rendered
form handlers, call the same typed service in `src/ixh26/flows/detection_settings.py` that the
JSON routes use. Use existing session and redirect conventions for browser auth.

### API

- `GET /api/detection-settings` returns
  `{ "version": 0, "thresholds": { ... }, "defaults": { ... }, "updated_at": null }`.
  Version 0 means factory defaults. After a save, `updated_at` is a UTC ISO 8601 timestamp.
- `PUT /api/detection-settings` takes `{ "version": <last read>, "thresholds": { ... } }`.
  Send every field. The success response is the same shape as GET and includes the new version.
  Restore defaults by filling the form with the returned `defaults` and saving against the
  current version. Use the returned defaults even if they differ from the values below.
- GET and PUT both require an authenticated analyst. Handle 401 and 403 using the app's
  session and access-denied behavior. For 422, map `detail[].loc` to the relevant field and
  preserve the draft. A 409 means another analyst saved a newer revision. Keep the draft and
  offer to load the latest settings for comparison before resubmitting.
- The profile is shared by analysts on the deployment's database. It applies on the worker's
  next detection run. Saving settings leaves existing findings as recorded and does not launch
  a historical replay. The live worker supplies inputs for funds funnels and possible wallet
  takeovers. Wash trading and liquidity withdrawal thresholds also persist and work on supplied
  fills and withdrawals. Label those two sections **Live data unavailable** until ledger
  ingestion supplies these events. The UI should not imply that editing them enables live scans.

### Form fields

Group the form into these four sections. Display windows in seconds or convert minutes to whole
seconds on submit. The API takes strict JSON integers for windows and counts. Their maximum is
2,147,483,647. Fractions and token amounts are plain decimal strings up to 64 characters
without exponent notation. Use exact decimal conversion if displaying percentages. XRP pool size
is a string of up to 18 whole-drop digits. One XRP equals 1,000,000 drops. Avoid binary floats for
amounts or percentage conversions.

| Group | Field | Label and meaning | Default | Accepted values |
|---|---|---|---:|---|
| Funds funnel | `funnel_window_seconds` | Lookback for incoming credits and shared destination | 1800 | Integer ≥ 1 second |
| Funds funnel | `funnel_min_senders` | Minimum distinct forwarding wallets on the same route | 3 | Integer ≥ 2 |
| Funds funnel | `funnel_min_fraction` | Minimum matched fraction of both incoming credits and the outgoing debit | `"0.8"` | Decimal string in (0, 1] |
| Wash trading | `wash_window_seconds` | Executed order-book trading lookback | 1800 | Integer ≥ 1 second |
| Wash trading | `wash_min_pair_fills` | Minimum fills between two wallets to connect them into a group | 2 | Integer ≥ 2 |
| Wash trading | `wash_min_fills` | Minimum executed fills within the group | 6 | Integer ≥ 2 |
| Wash trading | `wash_max_wallets` | Maximum distinct wallets in the group | 6 | Integer ≥ 2 |
| Wash trading | `wash_max_net_ratio` | Maximum net-to-gross trading ratio | `"0.15"` | Decimal string in [0, 1] |
| Wash trading | `wash_min_market_share` | Minimum share of observed market volume traded within the group | `"0.5"` | Decimal string in (0, 1] |
| Liquidity withdrawal | `liquidity_window_seconds` | Lookback for new buyers before the withdrawal | 3600 | Integer ≥ 1 second |
| Liquidity withdrawal | `liquidity_min_buyers` | Minimum distinct buyers whose token balance went from zero to positive | 3 | Integer ≥ 1 |
| Liquidity withdrawal | `liquidity_min_pool_drops` | Minimum XRP in the pool before the withdrawal | `"10000000"` | Positive whole-drop string |
| Liquidity withdrawal | `liquidity_min_drop` | Minimum fraction of XRP reserves removed | `"0.5"` | Decimal string in (0, 1] |
| Liquidity withdrawal | `liquidity_sale_size` | Token quantity for the before-and-after quote displayed in findings | `"1000"` | Positive decimal string in token units |
| Wallet takeover | `takeover_window_seconds` | Time allowed after a signing configuration change | 900 | Integer ≥ 1 second |
| Wallet takeover | `takeover_min_outflow` | Minimum share of starting balance sent to new destinations | `"0.7"` | Decimal string in (0, 1] |

Show the last saved time, a Save action, Restore defaults, validation feedback, and the shared
scope of the configuration. Test analyst-only access, grouping and units, persisted edits after
reload, restoring defaults, field errors, handling a version conflict, and the two market
sections' live-data labels.

## B. Mainnet and Testnet support

Backend branch `t/T-016-network-switch`. Read `GET /healthz` for the deployment's active
`network` and use it in the existing network indicator. The deployment setting
`XRPL_NETWORK` selects which ledger the worker monitors and which database the app uses. It is
an operator setting shared by the API and worker. Sign-in sessions and stored results belong
to their deployment network.

Add a signed-in transaction search with a 64-character hexadecimal hash field and a Mainnet or
Testnet selector. Call `GET /api/transactions/{tx_hash}?network=mainnet` or
`?network=testnet`. Omitting the query parameter uses the deployment network. The selector
controls only the lookup. Display the returned `network`, `hash`, `ledger_index`, `result`,
`transaction`, `metadata`, and `explorer_url` as appropriate. A validated transaction can
still have a failed execution result, so name both states clearly. Handle 404 for missing
transaction history, 409 for pending validation, 422 for invalid input, and 502 for lookup
failure. Test that changing the lookup network leaves the monitoring network unchanged.

## C. Watched wallet verification

Backend branch `t/T-017-wallet-verification`. Add verification to the signed-in wallet's
detail page. With `p = /api/wallets/{address}/verification`, implement:

1. `GET p` returns `{ "verified": <bool>, "tx_hash": <string|null>,
   "verified_at": <ISO timestamp|null> }`. Show proof status and link the confirmed hash
   to the correct network's explorer.
2. `POST p/challenge` has no body and returns 201 with `challenge_id`, `network`, `source`,
   `destination`, `destination_tag`, `amount_drops` (string), and `expires_at`.
   Show the network, source, funded recipient and exact destination tag prominently.
   The user sends **1 drop (0.000001 XRP)** plus the network fee using their own wallet.
   Give them copy controls for the recipient and tag and show the 15-minute expiry.
3. `POST p/confirm` accepts `{ "challenge_id": "...", "tx_hash": "..." }` and returns the
   same shape as GET on success. An identical successful confirmation can be retried.
   Distinguish recently submitted payments waiting for validation from used challenges
   using the server's detail. For 410, offer a fresh challenge. Show a useful message for 404
   (watch, challenge or payment missing), 422 (mismatch), 502 (lookup failed), and 503
   (recipient unavailable).

The operator configures the funded recipient for the active network. Keep payment approval in
the user's wallet. The application UI collects the public transaction hash only. Test successful
confirmation, pending validation, expiry, configuration unavailable, and another user's
verification being inaccessible using mocked ledger responses.

Run `make check` and exercise the changed pages in the browser. Report the tested flows and the
branches or commits included in the frontend base.
