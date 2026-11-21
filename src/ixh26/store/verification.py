"""Persistent challenge issuance and atomic consumption."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ColumnElement

from ixh26.store.models import Wallet, WalletChallenge, utcnow
from ixh26.store.repo import Store

CHALLENGE_TTL = timedelta(minutes=15)


def _watch_scope(wallet: Wallet, network: str) -> tuple[ColumnElement[bool], ...]:
    # SQLite can recycle a removed wallet's id. The creation time identifies the same watch.
    return (
        WalletChallenge.wallet_id == wallet.id,
        WalletChallenge.wallet_created_at == wallet.created_at,
        WalletChallenge.network == network,
    )


def issue_challenge(
    store: Store, wallet: Wallet, network: str, destination: str, after_ledger: int
) -> WalletChallenge:
    for attempt in range(5):
        row = WalletChallenge(
            id=uuid4().hex,
            wallet_id=wallet.id,
            wallet_created_at=wallet.created_at,
            network=network,
            destination=destination,
            destination_tag=secrets.randbelow(2**32 - 1) + 1,
            after_ledger=after_ledger,
            expires_at=utcnow() + CHALLENGE_TTL,
        )
        try:
            with store.session() as s:
                s.add(row)
                s.flush()
        except IntegrityError:
            if attempt == 4:
                raise
        else:
            return row
    raise AssertionError("unreachable")


def get_challenge(
    store: Store, wallet: Wallet, network: str, challenge_id: str
) -> WalletChallenge | None:
    with store.session() as s:
        return s.scalar(
            select(WalletChallenge).where(
                *_watch_scope(wallet, network), WalletChallenge.id == challenge_id
            )
        )


def get_proof(store: Store, wallet: Wallet, network: str) -> WalletChallenge | None:
    with store.session() as s:
        return s.scalar(
            select(WalletChallenge)
            .where(*_watch_scope(wallet, network), WalletChallenge.verified_at.is_not(None))
            .order_by(WalletChallenge.verified_at.desc())
            .limit(1)
        )


def confirm_challenge(
    store: Store, challenge_id: str, network: str, tx_hash: str, now: datetime
) -> bool:
    try:
        with store.session() as s:
            result = s.execute(
                update(WalletChallenge)
                .where(
                    WalletChallenge.id == challenge_id,
                    WalletChallenge.network == network,
                    WalletChallenge.expires_at > now,
                    WalletChallenge.payment_hash.is_(None),
                )
                .values(payment_hash=tx_hash, verified_at=now)
            )
            return result.rowcount == 1
    except IntegrityError:  # The same network and payment hash are already in use.
        return False
