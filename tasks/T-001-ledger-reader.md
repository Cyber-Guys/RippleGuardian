---
id: T-001
objective: O-1
status: done
owner: nico/claude
branch: t/T-001-ledger-reader
depends_on: [T-000]
scope: [src/ixh26/ledger/, tests/ledger/]
contracts_used: [Transfer, SecurityEvent]
policy: "1.0"
---
## Objective
`ledger/` reads an account's history (paginated account_tx) and live stream (subscribe) and normalises every value-moving tx into Transfer records.
## Acceptance criteria
- [x] Payment uses delivered_amount (partial payments), XRP + IOU
- [x] AccountDelete, CheckCash, EscrowFinish, PaymentChannelClaim produce Transfers
- [x] SetRegularKey / SignerListSet produce security events
- [x] Offline tests with recorded fixtures; one @network test on Testnet
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
- 23:45 nico/claude: ledger/normalize.py (pure), ledger/client.py (XrplReader with retry/backoff, XrplStream, submit helper). Gotcha: public Testnet node keeps ~2000 ledgers of history; one of its IPs times out intermittently, hence retries.
- 01:05 nico/claude: merged to master (fast-forward of the stacked chain) with nico's OK.
## Evidence
- tests/ledger/test_ledger_normalize.py (real Testnet payment fixture + delivered_amount, partial payment, security events, escrow/check/channel)
- tests/ledger/test_ledger_client.py (marker pagination, retry; @network current ledger passed)
