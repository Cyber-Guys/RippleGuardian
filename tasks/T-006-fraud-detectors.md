---
id: T-006
objective: O-1
status: claimed
owner: daniele/codex
branch: t/T-006-fraud-detectors
depends_on: [T-000]
scope: [src/ixh26/core/detection/, tests/core/test_detection.py, README.md]
contracts_used: [Asset, Amount, Transfer, SecurityEvent, AccountLabel]
policy: "1.0"
---
## Objective
Deliver four explainable backend detectors over normalized, validated XRPL activity.

## Acceptance criteria
- [ ] Detect rapid fan-in of one asset, with tagged destinations kept separate.
- [ ] Detect recurring, high-volume trading with little net change in individual wallet holdings.
- [ ] Detect a material AMM liquidity withdrawal after new buys and report the estimated impact on selling.
- [ ] Detect a signing configuration change followed by anomalous outflows to new destinations.
- [ ] Provide one callable batch interface and deterministic offline tests for positive cases and benign controls.

## Out of scope
Live ingestion, alert persistence, web UI, model training, and Mainnet. The existing reader and worker tasks own live integration.

## Log
- 21:49 daniele/codex: policy 1.0 acknowledged. Human authorized a new task for all four detectors from master, overriding D-001's deferral for this task.

## Evidence
