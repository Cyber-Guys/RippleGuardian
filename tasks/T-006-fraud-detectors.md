---
id: T-006
objective: O-1
status: done
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
- [x] Detect rapid fan-in of one asset, with tagged destinations kept separate.
- [x] Detect recurring, high-volume trading with little net change in individual wallet holdings.
- [x] Detect a material AMM liquidity withdrawal after new buys and report the estimated impact on selling.
- [x] Detect a signing configuration change followed by anomalous outflows to new destinations.
- [x] Provide one callable batch interface and deterministic offline tests for positive cases and benign controls.

## Out of scope
Live ingestion, alert persistence, web UI, model training, and Mainnet. The existing reader and worker tasks own live integration.

## Log
- 21:49 daniele/codex: policy 1.0 acknowledged. Human authorized a new task for all four detectors from master, overriding D-001's deferral for this task.
- 21:58 daniele/codex: implemented and moved to review. Next step is to wire the normalized-event interface into the ledger reader and alert worker when those tasks are available. Feed complete bounded windows and historical destinations. The AMM quotes cover the observed pool. Thresholds are starting values for replay.

- 01:05 nico/claude: merged to master (fast-forward of the stacked chain) with nico's OK.
## Evidence
- `tests/core/test_detection.py`: 11 offline cases, including distinct issuers and destination tags, reused credits, directional trading, small withdrawals, event ordering, and known destinations.
- `make check`: 33 tests passed, lint/format clean, and secret scan passed.
- `make smoke`: the existing Testnet skeleton smoke passed. Detector evidence comes from the offline tests above.
