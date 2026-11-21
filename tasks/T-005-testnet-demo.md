---
id: T-005
objective: O-1
status: done
owner: nico/claude
branch: t/T-005-testnet-demo
depends_on: [T-004]
scope: [scripts/, artifacts/, tests/scripts/, src/ixh26/ledger/ops.py, tests/ledger/test_ledger_ops.py]
contracts_used: []
policy: "1.0"
---
## Objective
`make demo` runs a scripted theft on Testnet (victim -> attacker split -> mule hops -> exchange + tag) and shows the backend tracing it.
## Acceptance criteria
- [x] Idempotent wallet setup via faucet, seeds only in .env
- [x] Every tx in artifacts/tx_log.jsonl with explorer link
- [x] Trace output reaches the exchange address + destination tag
## Out of scope
- Detection system, payments/subscriptions, mainnet.
## Log
- 23:10 nico/claude: policy 1.0 acknowledged. Claimed on nico's instruction (backend + frontend end-to-end). Branches are stacked: T-009 -> T-001 -> T-002 -> T-003 -> T-004 -> T-008 -> T-005; merge in that order.
- 00:55 nico/claude: scripts/new_wallets.py (VICTIM, EXCHANGE via faucet, seeds appended to .env, idempotent), scripts/demo.py (rekey -> drain to fresh attacker -> split to 3 fresh mules -> deposits at exchange tag 777001; attacker/mule key pairs are in-memory only), ledger/ops.py. Victim/exchange are topped up from the faucet when low, so the demo can be rerun. Gotcha: on this WSL machine IPv6 DNS lookups time out (5-15 s per connection); run with RES_OPTIONS="timeout:1 attempts:1" or fix /etc/resolv.conf.
- 01:05 nico/claude: merged to master (fast-forward of the stacked chain) with nico's OK.
## Evidence
Testnet run 2026-11-21 00:26 CET (artifacts/tx_log.jsonl, 8 txs), worker + API on sqlite:
- rekey https://testnet.xrpl.org/transactions/FBA56EC541F85EE5A32E95F856819501629C18B9C65A9CBB6C61A0F94D183FB0
- drain 98.89999 XRP https://testnet.xrpl.org/transactions/3F7C93D934C8F32BCD533A58178F95D19993F2D6E118A2F5E89FA53EACC9601C
- deposits tag 777001: 406ED1D2…, 75ECB8E8…, EDE0DBF8… (full hashes in tx_log.jsonl)
- user alerts: security_change, outgoing_payment, taint_at_exchange ("Traced 94.49999 XRP … tag 777001")
- findings: possible_takeover (victim, outflow 0.989 of balance), funds_funnel (exchange:777001, 3 senders)
- trace 1: 95.55% of the theft at Exchange (SIMULATED) tag 777001, hop 3; 1.1 XRP reserves left on each intermediate account
- tests/ledger/test_ledger_ops.py
