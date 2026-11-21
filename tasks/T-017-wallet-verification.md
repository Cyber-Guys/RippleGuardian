---
id: T-017
objective: O-1
status: review
owner: daniele/codex
branch: t/T-017-wallet-verification
depends_on: [T-001, T-003]
scope: [src/ixh26/config.py, src/ixh26/app/main.py, src/ixh26/app/verification.py, src/ixh26/store/models.py, src/ixh26/store/repo.py, src/ixh26/store/verification.py, src/ixh26/ledger/client.py, src/ixh26/flows/verification.py, tests/app/test_verification.py, tests/ledger/test_transactions.py]
contracts_used: []
policy: "1.0"
---

## Objective

Let a signed-in user prove control of a watched XRPL address by making a one-drop payment with a one-time destination tag.

## Acceptance criteria

- [x] Issue a short-lived challenge with the active network, recipient, amount, and tag.
- [x] Verify a final matching payment by hash and persist proof for the authenticated user's watched wallet.
- [x] Reject mismatches, old or unvalidated payments, replay, and challenges issued for another watch.

## Backend usage

1. Set `XRPL_VERIFICATION_RECIPIENT_TESTNET` to an operator-controlled, funded classic address
   that accepts tagged XRP payments. The suffix follows the configured network.
2. As a signed-in user, add the address to your watch list and call
   `POST /api/wallets/{address}/verification/challenge`. The response contains the source,
   recipient, amount in drops, and the one-time destination tag. The challenge lasts 15 minutes.
3. Send one drop (0.000001 XRP) from the watched wallet to that recipient with the supplied
   destination tag using your own wallet. The sender pays the network fee as usual. The backend
   only reads the ledger.
4. Call `POST /api/wallets/{address}/verification/confirm` with `challenge_id` and `tx_hash`.
   Call `GET /api/wallets/{address}/verification` for persisted proof status. The same successful
   confirmation may be retried. Removing a watched address removes access to its verification.

## Evidence

- `make check` passed with 92 offline tests. `make smoke` passed.
- API tests cover one-drop delivery, incorrect addresses or tag, expiry, failed or unvalidated
  transactions, replay, and ownership boundaries between users.
- A disposable PostgreSQL 16 database passed concurrent startup and single-use confirmation checks,
  including a destination tag at the upper end of the XRPL uint32 range.

## Log

- 2026-11-21 daniele/codex: policy 1.0 acknowledged. Human requested an isolated backend branch for payment-based verification. Task claimed on the branch after the merge freeze.
- 2026-11-21 daniele/codex: implementation verified and ready for review. Enable challenge issuance by configuring the funded recipient on the active network.
