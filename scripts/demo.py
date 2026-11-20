"""Live Testnet demo: a wallet takeover, a split across mules, and a deposit at an exchange.

Every transaction is real (Testnet) and logged to artifacts/tx_log.jsonl. The "exchange" is our
own wallet, labelled "Exchange (SIMULATED)". The attacker and mule wallets are throwaway key
pairs created for this run; their seeds stay in memory and are never stored.

Run the worker (`make worker` or docker compose) so alerts and findings appear in the app.
Usage: make demo ARGS="--watch-user alice --auto-trace analyst"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from decimal import Decimal

from ixh26 import config
from ixh26.contracts import XRP, AccountLabel, AccountLabelKind
from ixh26.ledger.client import XrplReader
from ixh26.ledger.ops import (
    base_reserve_drops,
    ensure_funded,
    ephemeral_wallet,
    pay_xrp,
    regular_key_of,
    set_regular_key,
)
from ixh26.store.repo import Store

XRP1 = Decimal(1_000_000)
EXCHANGE_TAG = 777001  # the "customer account" at the exchange
SPLIT = (Decimal("0.40"), Decimal("0.35"), Decimal("0.25"))
FEE_MARGIN = Decimal(100_000)  # 0.1 XRP kept back for fees on each hop


def step(text: str) -> None:
    print(f"\n== {text}")


async def wait_for_backfill(store: Store, address: str, timeout_s: int = 120) -> None:
    deadline = time.monotonic() + timeout_s
    while store.cursor(address) is None:
        if time.monotonic() > deadline:
            raise SystemExit("the worker has not synced the victim wallet; is `make worker` up?")
        await asyncio.sleep(2)


async def main(args: argparse.Namespace) -> int:
    settings = config.load_settings()
    store = Store.from_url(settings.database_url)
    reader = XrplReader(settings.network.json_rpc_url)
    reserve = await base_reserve_drops(settings)

    step("Preparing wallets (idempotent)")
    victim = await ensure_funded(settings, "VICTIM", 50 * XRP1)
    exchange = await ensure_funded(settings, "EXCHANGE", 2 * reserve)
    store.upsert_label(
        AccountLabel(exchange.classic_address, AccountLabelKind.EXCHANGE, "Exchange (SIMULATED)")
    )
    print("victim  ", victim.classic_address)
    print("exchange", exchange.classic_address, f"(deposit tag {EXCHANGE_TAG})")
    if args.watch_user:
        user = store.user_by_name(args.watch_user)
        if user is None:
            raise SystemExit(f"no user {args.watch_user!r}: register in the app first")
        if store.wallet(user.id, victim.classic_address) is None:
            store.add_wallet(user.id, victim.classic_address, "Savings")
        print(f"waiting for the worker to sync {args.watch_user}'s wallet…")
        await wait_for_backfill(store, victim.classic_address)

    attacker = ephemeral_wallet()
    step("1. The attacker, holding a stolen seed, adds their own signing key")
    if await regular_key_of(settings, victim.classic_address):
        await set_regular_key(settings, victim, None, "demo: reset previous regular key")
    r = await set_regular_key(settings, victim, attacker.classic_address, "demo: takeover rekey")
    print(r.explorer_url)

    step("2. Drain: everything above the reserve goes to a fresh attacker account")
    balance = await reader.xrp_balance(victim.classic_address)
    stolen = balance - reserve - FEE_MARGIN
    drain = await pay_xrp(
        settings,
        attacker,
        victim.classic_address,
        attacker.classic_address,
        stolen,
        "demo: drain",
    )
    print(f"{stolen / XRP1} XRP stolen at ledger {drain.ledger_index}: {drain.explorer_url}")

    step("3. Split across three fresh mule accounts")
    available = stolen - reserve - FEE_MARGIN
    mules = [ephemeral_wallet() for _ in SPLIT]
    sent = []
    for mule, share in zip(mules, SPLIT, strict=True):
        amount = (available * share).to_integral_value()
        r = await pay_xrp(
            settings,
            attacker,
            attacker.classic_address,
            mule.classic_address,
            amount,
            "demo: split to mule",
        )
        sent.append(amount)
        print(f"{amount / XRP1} XRP -> {mule.classic_address}: {r.explorer_url}")

    step("4. Mules deposit at the exchange under one customer tag")
    for mule, amount in zip(mules, sent, strict=True):
        deposit = amount - reserve - FEE_MARGIN
        r = await pay_xrp(
            settings,
            mule,
            mule.classic_address,
            exchange.classic_address,
            deposit,
            "demo: deposit at exchange",
            destination_tag=EXCHANGE_TAG,
        )
        print(f"{deposit / XRP1} XRP -> exchange tag {EXCHANGE_TAG}: {r.explorer_url}")

    step("Trace parameters")
    print(f"robbed wallet  {victim.classic_address}")
    print(f"stolen amount  {stolen / XRP1} XRP")
    print(f"from ledger    {drain.ledger_index}")
    if args.auto_trace:
        analyst = store.user_by_name(args.auto_trace)
        if analyst is None or analyst.role != "analyst":
            raise SystemExit(f"{args.auto_trace!r} is not an analyst account")
        row = store.create_trace(
            analyst.id, victim.classic_address, XRP, stolen, drain.ledger_index
        )
        print(f"queued trace {row.id}: open /analyst/traces/{row.id}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch-user", help="add the victim wallet to this user's watch list")
    parser.add_argument("--auto-trace", help="queue a trace as this analyst after the theft")
    logging.basicConfig(level=logging.WARNING)
    sys.exit(asyncio.run(main(parser.parse_args())))
