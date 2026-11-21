"""JSON endpoints for a signed-in user to prove control of their watched address."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ixh26 import config
from ixh26.app.api import require_address
from ixh26.app.auth import SettingsDep, StoreDep, UserDep
from ixh26.flows.verification import (
    TX_HASH_PATTERN,
    VERIFICATION_DROPS,
    LedgerError,
    TransactionNotFound,
    TransactionNotValidated,
    payment_matches,
    recipient_ledger,
)
from ixh26.store.models import Wallet, WalletChallenge, utcnow
from ixh26.store.repo import aware
from ixh26.store.verification import confirm_challenge, get_challenge, get_proof, issue_challenge

router = APIRouter(prefix="/api/wallets/{address}/verification")


class ChallengeOut(BaseModel):
    challenge_id: str
    network: str
    source: str
    destination: str
    destination_tag: int
    amount_drops: str
    expires_at: datetime


class Confirmation(BaseModel):
    challenge_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    tx_hash: str = Field(pattern=TX_HASH_PATTERN)


class VerificationOut(BaseModel):
    verified: bool
    tx_hash: str | None = None
    verified_at: datetime | None = None


def _wallet(address: str, user: UserDep, store: StoreDep) -> Wallet:
    row = store.wallet(user.id, require_address(address))
    if row is None:
        raise HTTPException(404, "watched wallet not found")
    return row


def _proof(row: WalletChallenge | None) -> VerificationOut:
    if row is None or row.verified_at is None:
        return VerificationOut(verified=False)
    return VerificationOut(
        verified=True, tx_hash=row.payment_hash, verified_at=aware(row.verified_at)
    )


@router.get("")
def verification_status(
    address: str, user: UserDep, store: StoreDep, settings: SettingsDep
) -> VerificationOut:
    return _proof(get_proof(store, _wallet(address, user, store), settings.network.name))


@router.post("/challenge", status_code=201)
async def create_challenge(
    address: str, user: UserDep, store: StoreDep, settings: SettingsDep
) -> ChallengeOut:
    wallet = _wallet(address, user, store)
    if get_proof(store, wallet, settings.network.name) is not None:
        raise HTTPException(409, "wallet is already verified")
    recipient = config.verification_recipient(settings.network)
    if not recipient:
        raise HTTPException(503, "wallet verification recipient is not configured")
    if recipient == wallet.address:
        raise HTTPException(422, "source and verification recipient must be different")
    try:
        after_ledger = await recipient_ledger(settings.network, recipient)
    except LedgerError as exc:
        raise HTTPException(502, "could not check the wallet verification recipient") from exc
    if after_ledger is None:
        raise HTTPException(503, "wallet verification recipient must be a funded classic address")
    row = issue_challenge(store, wallet, settings.network.name, recipient, after_ledger)
    return ChallengeOut(
        challenge_id=row.id,
        network=row.network,
        source=wallet.address,
        destination=row.destination,
        destination_tag=row.destination_tag,
        amount_drops=VERIFICATION_DROPS,
        expires_at=aware(row.expires_at),
    )


@router.post("/confirm")
async def verify_wallet(
    address: str, body: Confirmation, user: UserDep, store: StoreDep, settings: SettingsDep
) -> VerificationOut:
    wallet = _wallet(address, user, store)
    network = settings.network
    tx_hash = body.tx_hash.upper()
    row = get_challenge(store, wallet, network.name, body.challenge_id)
    if row is None:
        raise HTTPException(404, "wallet verification challenge not found")
    if row.payment_hash == tx_hash:
        return _proof(row)
    if row.payment_hash is not None:
        raise HTTPException(409, "wallet verification challenge already used")
    if aware(row.expires_at) <= utcnow():
        raise HTTPException(410, "wallet verification challenge expired")
    try:
        matches = await payment_matches(network, wallet.address, row, tx_hash)
    except TransactionNotFound as exc:
        raise HTTPException(404, "payment not found on the challenge network") from exc
    except TransactionNotValidated as exc:
        raise HTTPException(409, "payment is not yet validated") from exc
    except LedgerError as exc:
        raise HTTPException(502, "payment lookup failed") from exc
    if not matches:
        raise HTTPException(422, "payment does not match the wallet verification challenge")
    now = utcnow()
    if aware(row.expires_at) <= now:
        raise HTTPException(410, "wallet verification challenge expired")
    if not confirm_challenge(store, row.id, network.name, tx_hash, now):
        current = get_challenge(store, wallet, network.name, row.id)
        if current is not None and current.payment_hash == tx_hash:
            return _proof(current)
        raise HTTPException(409, "wallet verification payment or challenge already used")
    return VerificationOut(verified=True, tx_hash=tx_hash, verified_at=now)
