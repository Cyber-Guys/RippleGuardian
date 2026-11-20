"""Create the persistent demo wallets on Testnet (faucet) and append their seeds to .env.

Idempotent: wallets whose XRPL_SEED_<NAME> is already set are left alone. Seeds are written
straight to .env and never printed (CLAUDE.md §6). Run via `make wallets`.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from ixh26 import config
from ixh26.ledger.ops import new_faucet_seed

NAMES = ("VICTIM", "EXCHANGE")  # attacker and mules are throwaway wallets made per demo run
ENV_FILE = Path(".env")


async def main() -> int:
    settings = config.load_settings()
    missing = [name for name in NAMES if not config.has_wallet_seed(name)]
    if not missing:
        print("demo wallets already configured:", ", ".join(NAMES))
        return 0
    if not ENV_FILE.exists():
        print(".env not found: run `make setup` first", file=sys.stderr)
        return 1
    for name in missing:
        address, seed = await new_faucet_seed(settings)
        with ENV_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"\nXRPL_SEED_{name}={seed}\n")
        print(f"created {name.lower()} wallet {address} (seed saved to .env)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
