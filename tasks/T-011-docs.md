---
id: T-011
objective: O-1
status: done
owner: nico/claude
branch: t/T-011-docs
depends_on: [T-012, T-013]
scope: [README.md, docs/, src/ixh26/**/README.md]
contracts_used: []
policy: "1.0"
---
## Objective
Docs that let any agent or teammate understand the idea (and how it changed), the architecture and how to run and verify it.
## Acceptance criteria
- [x] README per CLAUDE.md §8 (pitch, diagram, quickstart, claim->evidence, SIMULATED, roadmap, team)
- [x] docs/CONTEXT.md (idea history, pivots, glossary), docs/ARCHITECTURE.md with code snippets
- [x] docs/DESIGN.md threat model, docs/SUBMISSION.md draft, D-007
## Out of scope
Mainnet, Clawback/Freeze, new detectors.
## Log
- 01:10 nico/claude: policy 1.0 acknowledged. Created on nico's instruction.
- 02:20 nico/claude: README rewritten (CLAUDE.md §8 order), docs/CONTEXT.md (idea history and glossary), docs/ARCHITECTURE.md (code excerpts, graphify check), docs/DESIGN.md (threat model), docs/SUBMISSION.md draft with TODOs for humans, D-007, D-008. Plain-English pass with the humanizer skill. Merged to master with nico's OK.
## Evidence
- the files above; every README claim links a test, a tx or docs/E2E.md
