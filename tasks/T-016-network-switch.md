---
id: T-016
objective: O-1
status: review
owner: daniele/codex
branch: t/T-016-network-switch
depends_on: [T-001, T-003, T-004]
scope: [src/ixh26/config.py, src/ixh26/app/main.py, src/ixh26/app/api.py, src/ixh26/app/auth.py, src/ixh26/store/models.py, src/ixh26/store/repo.py, src/ixh26/ledger/client.py, src/ixh26/cli.py, src/ixh26/flows/worker.py, src/ixh26/flows/transactions.py, scripts/demo.py, tests/test_config.py, tests/store/test_network_store.py, tests/app/test_transaction_api.py, tests/ledger/test_transactions.py]
contracts_used: [AccountActivity]
policy: "1.0"
---

## Objective

Select Mainnet or Testnet for monitoring and stored analysis, and make XRPL transactions searchable by hash on either network.

## Acceptance criteria

- [x] Testnet remains the default. Mainnet monitoring and traces use a separate database and reject Testnet sessions.
- [x] An authenticated request can fetch a validated transaction by hash on either network.
- [x] The submission path refuses Mainnet before contacting an XRPL server.

## Backend usage

- Set `XRPL_NETWORK=testnet` (default) or `XRPL_NETWORK=mainnet` for both the API and the
  worker and restart them. Mainnet requires `XRPL_MAINNET_DATABASE_URL` pointing to a separate,
  provisioned database. Testnet continues to use `DATABASE_URL`. Create users and add watched
  wallets in the selected deployment. Sign in again after changing networks.
- `GET /healthz` reports the deployment network. Authenticated
  `GET /api/transactions/{hash}?network=mainnet` looks up a validated transaction, including its
  result, metadata, and explorer link. Use `network=testnet` for a Testnet hash or omit the query
  parameter to use the deployment network. The query parameter applies only to that lookup.
- Hash lookup returns 404 when the selected server lacks the transaction and 409 when the server
  finds it before validation. Final transactions with failed execution still return their metadata.

## Evidence

- Offline API tests cover per-request network selection, wrong-network sessions, malformed inputs,
  legacy data isolation, and the Mainnet submission guard. `make check` and `make smoke` passed.
- A disposable PostgreSQL 16 database passed concurrent first startup and network isolation checks.
- Read-only RPC retrieved a validated Mainnet `OfferCreate` and Testnet `Payment` by hash.

## Log

- 2026-11-21 daniele/codex: policy 1.0 acknowledged. Human requested an isolated backend branch with Mainnet reads. Task claimed on the branch after the merge freeze.
- 2026-11-21 daniele/codex: implementation verified and ready for review. Deploy the API and worker with the same network and database settings.
