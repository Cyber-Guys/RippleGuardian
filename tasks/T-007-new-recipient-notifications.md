---
id: T-007
objective: O-1
status: claimed
owner: daniele/codex
branch: t/T-007-new-recipient-notifications
depends_on: [T-000]
scope: [src/ixh26/app/main.py, src/ixh26/app/notifications.py, src/ixh26/app/notifications.html, src/ixh26/flows/notifications.py, src/ixh26/ledger/notification_history.py, tests/app/test_notifications.py, tests/ledger/test_notification_history.py, README.md]
contracts_used: [NetworkEndpoints]
policy: "1.0"
---
## Objective
Show a notification for a validated XRP payment above a configurable amount to a new recipient.

## Acceptance criteria
- [ ] Notifications page accepts a Testnet address and a threshold in XRP, with a default of 10 XRP.
- [ ] Detect the first successful outbound payment to each address in available account history, using the delivered amount and a strict threshold. Older payments establish recipient familiarity.
- [ ] Refresh the visible feed and show the recipient, delivered XRP, time, and transaction evidence.
- [ ] Test matching, excluded payments, pagination, and the page against an injected offline reader.

## Out of scope
Mainnet, push/email delivery, hosted accounts, and background persistence. The page monitors the selected address while open.

## Log
- 22:27 daniele/codex: policy 1.0 acknowledged. User requested an unknown-recipient notification. The shared branch contains no app or worker yet, so this task delivers the page and its Testnet read-only feed using the existing API entry point.

## Evidence
