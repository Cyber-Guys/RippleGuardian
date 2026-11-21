# Design and threat model

## Problem and users

People who hold XRP or tokens in their own wallet have no one watching it for them. When a seed leaks, the thief usually adds a signing key, drains the wallet and moves the money through a few new accounts to an exchange, all in a few minutes. Ripple Guardian is for two groups: the owner, who needs to know at once and in plain words what happened and what to do, and an analyst, who needs to follow the money and tell the exchange which deposit tag to freeze.

XRPL fits this better than most chains for two reasons. Every payment records what it actually delivered (`delivered_amount`), so amounts can be trusted. And deposits to exchanges carry a destination tag that identifies one customer account, so a trace can end at "this exchange, this customer" rather than "a big exchange wallet".

## Architecture

```
 browser ──(cookie, SameSite=Lax)──▶ api ──▶ store (Postgres)
                                            ▲
 XRPL Testnet ──(WebSocket + JSON-RPC)──▶ worker
```

Trust boundaries: the browser is untrusted, the api trusts only its session cookie and its database, and the worker trusts only validated ledger data. Nothing in the product signs a transaction or holds a user's key. Only the demo script signs, with Testnet wallets whose seeds live in `.env`.

## How the product uses XRPL

| Purpose | Transactions and objects | Network | Status |
|---|---|---|---|
| Watch wallets live | `subscribe` (accounts), `account_tx` | Testnet | real |
| Read value moved | Payment (`delivered_amount`), AccountDelete, CheckCash, EscrowFinish, PaymentChannelClaim | Testnet | real |
| Spot takeovers | SetRegularKey, SignerListSet, AccountSet (disable master), AccountDelete | Testnet | real |
| Opening balance for haircut | `account_info` at the ledger before the theft | Testnet | real; falls back to 0 with a note when history is pruned |
| Exchange identification | destination tag on deposits | Testnet | real tags, two exchange wallets of our own (SIMULATED labels) |
| Demo theft | SetRegularKey, Payment, with SourceTag and a memo | Testnet | real |

## Main flows

1. An owner registers with a username and adds a wallet address. The worker reads its history without sending alerts, then watches it.
2. A key change or outgoing payment arrives over WebSocket. The owner sees a notification within seconds, and the wallet's status turns red with a list of steps.
3. The takeover detector raises a finding for analysts. An analyst starts a trace from it.
4. The trace follows the money to the exchange and tag. The owner gets a notification with the exchange, the tag and the amount, and analysts can flag the mule accounts.
5. Any user can look up an address before paying it, and gets an alert if one of their wallets deals with a flagged account.

## Threat model

| Actor | Can do | Mitigation | What remains |
|---|---|---|---|
| Thief who holds a victim's seed | Rekey, drain, launder through new accounts | Alerts on rekey and outflow; takeover and funnel detectors; tracing to the exchange tag | We can tell, not stop. Getting the money back needs the exchange or, for tokens, the issuer (roadmap). |
| Attacker sending partial payments | Make a payment look larger than it is | Amounts come only from `delivered_amount`; `unavailable` raises | none known |
| Launderer splitting funds into dust | Push branches below the trace threshold | 1% / 1 XRP floor, reported as `truncated` | Dust below the floor is not followed. |
| Launderer mixing with clean funds | Dilute the taint | Haircut model shows the diluted share honestly | A different model (FIFO, poison) would attribute differently; we show the model on every trace. |
| Launderer swapping on the DEX | Change currency mid-route | Same-asset tracing only | Cross-currency taint is roadmap. |
| Careless or malicious analyst | Flag an innocent account | Flags show category, reason and analyst name; can be revoked; analysts are created only from the CLI | A wrong flag is visible to users until revoked. |
| Someone watching a stranger's wallet | Add any address | Addresses and their history are already public on the ledger | No ownership proof yet (roadmap: tagged micro-payment). |
| Web attacker | Session theft, CSRF, role escalation | argon2 password hashes, signed JWT in an HttpOnly cookie, SameSite=Lax, role checked on every analyst route and API call, Jinja2 autoescaping | Cookie is not `Secure` (local demo over http). No rate limit on login. |
| Secret leak through the repo | Commit a seed | Seeds only in `.env`, git-ignored; a secret scan in `make check` fails on seed patterns | Human error outside the repo. |
| Public node outage | Missed transactions | Polling catch-up from the cursor; retries with backoff | The public Testnet node keeps about 2 hours of history; a longer outage loses older activity. |

## Limitations and simulated parts

- Exchange and Exchange B are our own Testnet wallets with a label. No real exchange receives evidence yet.
- Redis is in `docker-compose.yml` and `config.py` reads `REDIS_URL`, but no code uses it yet.
- Two of the four detectors (wash trading, liquidity drop) get no live data, because DEX fills and AMM withdrawals are not read yet.
- Detection runs on watched wallets and on accounts visited by traces, not on the whole ledger.
- Thresholds (15 and 30 minute windows, 70% outflow, 1% taint floor) are starting values, not calibrated on real thefts.
- The database schema is created at startup; there are no migrations.
- Notifications are in-app only; an owner who never opens the app is not reached.

## Roadmap (not built)

- Issuer freeze and clawback for stolen tokens, using the trace as evidence.
- Wallet ownership proof with a tagged micro-payment.
- DEX and AMM data for cross-currency tracing and the two market detectors.
- Opt-in push or email.
- Mainnet, after review with an exchange.
