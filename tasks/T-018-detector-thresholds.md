---
id: T-018
objective: O-1
status: review
owner: daniele/codex
branch: t/T-018-detector-thresholds
depends_on: [T-003, T-004, T-006]
scope: [src/ixh26/core/detection/models.py, src/ixh26/core/detection/markets.py, src/ixh26/app/api.py, src/ixh26/app/detection_settings.py, src/ixh26/flows/detection_settings.py, src/ixh26/flows/monitor.py, src/ixh26/store/models.py, src/ixh26/store/repo.py, src/ixh26/store/detection_settings.py, tests/app/test_detector_settings_api.py, tests/core/test_detection.py, README.md, docs/ARCHITECTURE.md, docs/FRONTEND-BACKEND-HANDOFF.md]
contracts_used: []
policy: "1.1"
---

## Objective

Let analysts configure the thresholds of the four fraud rules and give a frontend agent a complete integration prompt.

## Acceptance criteria

- [x] The analyst API returns current and default thresholds and validates updates to all four rules.
- [x] Settings persist and the worker picks them up on its next detection run.
- [x] Stale edits cannot replace a more recent configuration.
- [x] The frontend prompt describes the API contract, control labels and units, role, and current worker coverage.

## Out of scope

Frontend implementation, DEX and AMM live ingestion, and historical replay on save.

## Log

- 10:50 daniele/codex: policy 1.0 acknowledged. Human authorized a separate backend branch and requested a frontend handoff prompt. Task claimed on its feature branch.
- 10:58 daniele/codex: policy 1.1 acknowledged after fetching the rewritten `origin/master`. Applying the policy's verification and doc review steps by hand.
- 11:01 daniele/codex: ready for review. Use the frontend handoff to implement analyst controls. Market rules still need live ingestion for fills and withdrawals.

## Evidence

- `make check` passed with 93 offline tests. `make smoke` passed.
- `tests/app/test_detector_settings_api.py` covers role enforcement, all 16 values, exact amount and
  ratio round-trips, stale saves, defaults, validation, and updates picked up by a running monitor.
- `tests/core/test_detection.py::test_wash_trading_uses_configurable_fill_count_per_pair` verifies
  that the pair-fill threshold affects detection.
- In a disposable PostgreSQL 16 database, two connections initialized the schema concurrently and
  competing saves for version 0 produced exactly one committed revision.
- [Frontend prompt](../docs/FRONTEND-BACKEND-HANDOFF.md) includes the threshold editor and the
  earlier network switch and wallet verification contracts.
