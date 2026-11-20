---
id: T-001
objective: O-1
status: todo
owner: tommaso/a1
branch: t/T-001-ledger-reader
depends_on: [T-000]
scope: [src/ixh26/ledger/, tests/ledger/]
contracts_used: [Transfer, SecurityEvent]
policy: "1.0"
---
## Objective
`ledger/` reads an account's history (paginated account_tx) and live stream (subscribe) and normalises every value-moving tx into Transfer records.
## Acceptance criteria
- [ ] Payment uses delivered_amount (partial payments), XRP + IOU
- [ ] AccountDelete, CheckCash, EscrowFinish, PaymentChannelClaim produce Transfers
- [ ] SetRegularKey / SignerListSet produce security events
- [ ] Offline tests with recorded fixtures; one @network test on Testnet
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
## Evidence
