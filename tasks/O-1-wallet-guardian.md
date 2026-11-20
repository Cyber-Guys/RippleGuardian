---
id: O-1
owner: tommaso
criterion: [Execution, Impact, Pitch]
tasks: [T-000, T-001, T-002, T-003, T-004, T-005, T-006, T-008, T-009]
---
## Outcome
A judge watches, live on Testnet, a monitored wallet get "robbed" (funds split across attacker
wallets and laundered), and our dockerized backend alerts the owner and traces the stolen funds
hop by hop with haircut taint (1% threshold), ending at an exchange-like address + destination tag.

## Notes
- Testnet only (CLAUDE.md §5). The theft scenario is scripted but every tx hash is real.
- Detection system and paid subscription are out of scope (roadmap).
