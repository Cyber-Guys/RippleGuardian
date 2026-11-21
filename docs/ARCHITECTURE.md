# Architecture

This page follows one theft through the code, from the ledger to the screen. The excerpts are copied from the source and kept short; the file and function names let you jump to the full version.

## Modules and who may import what

```
contracts.py   shared frozen types (Transfer, SecurityEvent, Alert, TraceResult, ...)
config.py      the only reader of environment variables

ledger/        the only code that imports xrpl-py
  normalize.py   raw transaction JSON -> Transfer, SecurityEvent, PreTxBalance
  client.py      XrplReader (JSON-RPC, retries), XrplStream (WebSocket), submit()
  ops.py         Testnet helpers for the demo (faucet, rekey, pay)
core/          pure functions, no I/O
  alerts.py      which alert a ledger event deserves
  taint.py       haircut taint propagation
  detection/     four detectors (T-006)
store/         SQLAlchemy tables and queries (Postgres in docker, SQLite in tests)
flows/         joins the above
  monitor.py     save activity -> alert owners -> run detectors
  trace.py       trace job: fetch hop by hop, compute taint, alert the victim
  trace_report.py  TraceResult -> the JSON the pages read
  report.py      incident for a robbed owner: recovery steps, PDF with tx links and a SHA-256 fingerprint
  worker.py      the long-running process: stream, polling, trace jobs
  smoke.py       the same path offline on SIMULATED data (make smoke)
app/           FastAPI: JSON API, web pages, SVG charts (balance line, hop graph). Uses the store, never XRPL.
```

`core` never imports `ledger`, `store` or `app`, so every rule can be tested with plain objects. A code graph built with graphify over `src/` (743 nodes, 2,291 edges) has `AccountActivity`, `Amount`, `Asset`, `Settings`, `Monitor` and the page `render()` helper as its most connected nodes, which is the shape we want: the shared contracts in the middle, one orchestrator, one rendering path.

## 1. Reading the ledger

The worker learns about transactions in two ways. A WebSocket subscription delivers each validated transaction of a watched wallet within seconds. Every few seconds a polling loop asks `account_tx` for everything since the wallet's cursor, which covers anything the socket missed. Both paths hand the same `AccountActivity` to the monitor, and the store ignores what it already has.

`flows/worker.py`:

```python
async def catch_up(reader: XrplReader, monitor: Monitor) -> None:
    """Process everything since each wallet's cursor. New wallets backfill without alerts."""
    current = await reader.current_ledger()
    for address in monitor.store.watched_addresses():
        cursor = monitor.store.cursor(address)
        start = EARLIEST if cursor is None else cursor + 1
        ...
        for activity in await reader.account_activity(
            address, from_ledger=start, to_ledger=current
        ):
            monitor.process(activity, notify=cursor is not None)
        monitor.store.set_cursor(address, current)
```

A wallet added a minute ago has no cursor, so its old history is stored without sending a burst of old alerts.

## 2. Turning raw JSON into transfers

Each transaction type that moves value has its own small extractor. `ledger/normalize.py`:

```python
EXTRACTORS: dict[str, Callable[[TxContext], list[Transfer]]] = {
    "Payment": _payment,
    "AccountDelete": _account_delete,
    "CheckCash": _check_cash,
    "EscrowFinish": _escrow_finish,
    "PaymentChannelClaim": _channel_claim,
}
```

Payments always use `delivered_amount` from the metadata. A partial payment can request a large `Amount` and deliver almost nothing, and trusting `Amount` would let an attacker fake both thefts and alerts. If the ledger says `delivered_amount` is `unavailable`, normalisation raises instead of guessing. Key changes (`SetRegularKey`, `SignerListSet`, disabling the master key, deleting the account) become `SecurityEvent`s. For each sender the metadata also gives the balance just before the transaction, which the takeover detector needs.

## 3. Deciding who to tell

The rules are pure functions in `core/alerts.py`. One rule per kind of alert:

```python
def alerts_for(transfers, events, flags, now) -> list[Alert]:
    """Every alert the new ledger activity deserves, before owners' preferences."""
    alerts = [security_alert(e, now) for e in events]
    for t in transfers:
        alerts.append(outgoing_alert(t, now))
        alerts.extend(flagged_contact_alerts(t, flags, now))
    return alerts
```

`flows/monitor.py` then applies each owner's settings for that wallet:

```python
def wants(wallet: Wallet, alert: Alert, drops: Decimal | None) -> bool:
    if alert.kind is AlertKind.SECURITY_CHANGE:
        return wallet.notify_security
    if alert.kind is AlertKind.FLAGGED_COUNTERPARTY:
        return wallet.notify_flagged
    if alert.kind is AlertKind.OUTGOING_PAYMENT:
        above_threshold = drops is None or drops >= Decimal(wallet.min_outgoing_drops)
        return wallet.notify_outgoing and above_threshold
    return True
```

Several users can watch the same address; each one gets their own copy, filtered by their own settings.

## 4. Detectors

After storing new activity the monitor rebuilds a `DetectionBatch` from the stored history of the accounts involved and runs `core.detection.detect`. Findings are stored once per (detector, subject, triggering transaction), so running the rules again over the same history adds nothing. Two rules matter for a theft:

- Possible takeover: a signing change followed within 15 minutes by outflows to new destinations worth at least 70% of the balance.
- Funds funnel: at least three accounts forward most of what they just received to the same destination and tag within 30 minutes.

The full rule descriptions and thresholds are in `core/detection/models.py` (`DetectionSettings`) and `tests/core/test_detection.py`.

## 5. Tracing the money

An analyst starts a trace with the robbed wallet, the stolen amount and the ledger of the theft. The trace job (`flows/trace.py`) fetches the victim's transfers, computes taint, adds every account that received stolen funds to the next round, and repeats until no new account appears or the hop limit is reached. Accounts with a label (an exchange, an issuer) end the trace. They also become sinks, split by destination tag.

The rule itself is a few lines in `core/taint.py`:

```python
for t in ordered:  # every transfer, in ledger order
    ...
    if taint[src] > 0 and src not in labels:
        if src == params.origin:
            carried = min(amount, taint[src])
        else:
            carried = min(taint[src], amount * taint[src] / max(balance[src], amount))
    balance[src] = max(balance[src] - amount, Decimal(0))
    balance[dst] += amount
    ...
    if carried < floor or next_hop > params.max_hops:
        truncated = True
        continue
    edges.append(TaintEdge(t, next_hop, carried, carried / amount))
```

`balance[src]` starts from the account's balance just before the theft (queried at `start_ledger - 1`), so a mule that already held clean XRP passes on a proportionally smaller stolen share. Payments made before the stolen funds arrived carry no taint, because the loop walks transfers in ledger order. Below 1% of the theft, or 1 XRP, a branch is not followed.

When the trace ends at a labelled exchange, the victim gets a notification naming the exchange, the tag and the amount.

## 6. Writing to the ledger (demo only)

The product reads the ledger and never signs anything. The demo script does write, and every write goes through one helper in `ledger/client.py`:

```python
async def submit(settings, tx, wallet, purpose, *, tx_log=TX_LOG) -> TxResult:
    """The ONLY submission path: SourceTag + memo, submit_and_wait, require tesSUCCESS, log."""
    memo = Memo(
        memo_type=str_to_hex("ixh26/purpose"),
        memo_data=str_to_hex(f"{config.APP_ID}:{purpose}"[:120]),
    )
    tx = replace(tx, source_tag=settings.source_tag, memos=[*(tx.memos or []), memo])
    ...
```

Anything other than a validated `tesSUCCESS` raises. Every success is appended to `artifacts/tx_log.jsonl` with its explorer link. The demo's attacker and mule wallets are created in memory for one run, and their seeds are never written anywhere.

## 7. The web app

`app/web.py` mounts one router per area: `views/auth_pages.py`, `user_pages.py`, `flag_pages.py` and `analyst_pages.py`. View models in `views/models.py` turn rows into what a page shows. For example, `wallet_state()` picks the most serious condition of a wallet (compromised, then flagged, then risky contact) and attaches the steps the owner should take.

Charts are SVG built on the server by pure functions in `app/charts.py`, so there is no JavaScript to write or audit. HTMX refreshes the notification count and feed every five seconds, and the trace page while a trace is running. The look is described in [DECISIONS.md](DECISIONS.md) (D-007), and every token lives at the top of `app/static/app.css`.

Two roles are enforced on the server. Page dependencies raise `LoginRequired` (redirect to `/login`) or `AnalystOnly` (403). The JSON API under `/api` applies the same rules.

## Testing

| Command | What it covers | Network |
|---|---|---|
| `make check` | lint, format, 73 offline tests, secret scan | no |
| `make smoke` | the whole path on the SIMULATED scenario in `flows/smoke.py` | no |
| `make test-network` | reader against Testnet | yes |
| `make demo` | a real theft on Testnet | yes |
| `scripts/e2e_browser.py` | both roles in a real browser against a running app | local app |
