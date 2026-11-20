"""JSON API (``/api``): users see their own wallets; analysts see findings, traces, flags."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ixh26.app import auth
from ixh26.app.auth import AnalystDep, SettingsDep, StoreDep, UserDep
from ixh26.contracts import XRP, Asset
from ixh26.store.repo import Store

router = APIRouter(prefix="/api")

FLAG_CATEGORIES = ("theft", "scam", "phishing", "mixer", "wash_trading", "rug_pull", "other")


class Credentials(BaseModel):
    username: str
    password: str


class WalletIn(BaseModel):
    address: str
    label: str = Field(default="", max_length=40)


class WalletSettings(BaseModel):
    label: str | None = Field(default=None, max_length=40)
    notify_outgoing: bool | None = None
    notify_security: bool | None = None
    notify_flagged: bool | None = None
    min_outgoing_xrp: str | None = None


class FlagIn(BaseModel):
    target_type: str = "account"
    target: str
    category: str = "other"
    reason: str = Field(min_length=3, max_length=280)
    finding_id: int | None = None


class TraceIn(BaseModel):
    origin: str
    stolen_xrp: str
    start_ledger: int = Field(ge=1)
    currency: str = "XRP"
    issuer: str | None = None


class ReadIn(BaseModel):
    ids: list[int] | None = None


def parse_decimal(raw: str, field: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise HTTPException(422, f"{field}: not a number") from None
    if not value.is_finite() or value < 0:
        raise HTTPException(422, f"{field}: must be a non-negative number")
    return value


def xrp_to_drops(raw: str, field: str) -> Decimal:
    drops = parse_decimal(raw, field) * 1_000_000
    if drops != drops.to_integral_value():
        raise HTTPException(422, f"{field}: at most 6 decimals")
    return Decimal(int(drops))


def require_address(address: str) -> str:
    address = address.strip()
    if not auth.ADDRESS_RE.fullmatch(address):
        raise HTTPException(422, "not a valid XRPL classic address")
    return address


def wallet_settings_fields(body: WalletSettings) -> dict[str, Any]:
    fields = body.model_dump(exclude_none=True, exclude={"min_outgoing_xrp"})
    if body.min_outgoing_xrp is not None:
        fields["min_outgoing_drops"] = str(xrp_to_drops(body.min_outgoing_xrp, "threshold"))
    return fields


def add_flag(store: Store, analyst_id: int, body: FlagIn) -> int:
    if body.category not in FLAG_CATEGORIES:
        raise HTTPException(422, f"category must be one of {FLAG_CATEGORIES}")
    if body.target_type == "account":
        target = require_address(body.target)
    elif body.target_type == "tx" and auth.TX_HASH_RE.fullmatch(body.target.strip()):
        target = body.target.strip().upper()
    else:
        raise HTTPException(422, "target must be an account address or a 64-hex tx hash")
    flag = store.add_flag(
        body.target_type, target, body.category, body.reason, analyst_id, body.finding_id
    )
    if body.finding_id is not None:
        store.set_finding_status(body.finding_id, "flagged")
    return flag.id


def start_trace(store: Store, analyst_id: int, body: TraceIn) -> int:
    origin = require_address(body.origin)
    if body.currency == "XRP":
        asset, stolen = XRP, xrp_to_drops(body.stolen_xrp, "stolen amount")
    else:
        asset = Asset(body.currency, require_address(body.issuer or ""))
        stolen = parse_decimal(body.stolen_xrp, "stolen amount")
    if stolen <= 0:
        raise HTTPException(422, "stolen amount must be positive")
    return store.create_trace(analyst_id, origin, asset, stolen, body.start_ledger).id


# --- auth -------------------------------------------------------------------------------------


@router.post("/register", status_code=201)
def register(body: Credentials, store: StoreDep) -> dict[str, Any]:
    auth.validate_credentials(body.username, body.password)
    if store.user_by_name(body.username):
        raise HTTPException(409, "username taken")
    user = store.create_user(body.username, auth.hash_password(body.password))
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/login")
def login(
    body: Credentials, store: StoreDep, settings: SettingsDep, response: Response
) -> dict[str, str]:
    user = auth.authenticate(store, body.username, body.password)
    token = auth.issue_token(user, settings)
    response.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax")
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/me")
def me(user: UserDep) -> dict[str, Any]:
    return {"id": user.id, "username": user.username, "role": user.role}


# --- user: wallets & notifications ------------------------------------------------------------


@router.get("/wallets")
def list_wallets(user: UserDep, store: StoreDep) -> list[dict[str, Any]]:
    return [
        {
            "address": w.address,
            "label": w.label,
            "notify_outgoing": w.notify_outgoing,
            "notify_security": w.notify_security,
            "notify_flagged": w.notify_flagged,
            "min_outgoing_drops": w.min_outgoing_drops,
        }
        for w in store.wallets(user.id)
    ]


@router.post("/wallets", status_code=201)
def add_wallet(body: WalletIn, user: UserDep, store: StoreDep) -> dict[str, str]:
    address = require_address(body.address)
    if store.wallet(user.id, address):
        raise HTTPException(409, "already watched")
    store.add_wallet(user.id, address, body.label)
    return {"address": address}


@router.patch("/wallets/{address}")
def patch_wallet(address: str, body: WalletSettings, user: UserDep, store: StoreDep) -> dict:
    if not store.wallet(user.id, address):
        raise HTTPException(404, "not one of your wallets")
    store.update_wallet(user.id, address, **wallet_settings_fields(body))
    return {"ok": True}


@router.delete("/wallets/{address}", status_code=204)
def delete_wallet(address: str, user: UserDep, store: StoreDep) -> None:
    store.remove_wallet(user.id, address)


@router.get("/alerts")
def list_alerts(user: UserDep, store: StoreDep, unread: bool = False) -> list[dict[str, Any]]:
    return [
        {
            "id": a.id,
            "wallet": a.wallet,
            "kind": a.kind,
            "severity": a.severity,
            "tx_hash": a.tx_hash,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
            "read": a.read,
        }
        for a in store.alerts(user.id, unread_only=unread)
    ]


@router.post("/alerts/read")
def read_alerts(body: ReadIn, user: UserDep, store: StoreDep) -> dict[str, bool]:
    store.mark_read(user.id, body.ids)
    return {"ok": True}


# --- shared: analyst flags are visible to every logged-in user --------------------------------


@router.get("/flags")
def list_flags(user: UserDep, store: StoreDep) -> list[dict[str, Any]]:
    return [
        {
            "id": f.id,
            "target_type": f.target_type,
            "target": f.target,
            "category": f.category,
            "reason": f.reason,
            "analyst": analyst_name,
            "created_at": f.created_at.isoformat(),
        }
        for f, analyst_name in store.flags()
    ]


# --- analyst ----------------------------------------------------------------------------------


@router.post("/flags", status_code=201)
def create_flag(body: FlagIn, user: AnalystDep, store: StoreDep) -> dict[str, int]:
    return {"id": add_flag(store, user.id, body)}


@router.delete("/flags/{flag_id}", status_code=204)
def revoke_flag(flag_id: int, user: AnalystDep, store: StoreDep) -> None:
    store.revoke_flag(flag_id)


@router.get("/findings")
def list_findings(
    user: AnalystDep, store: StoreDep, status: str | None = None
) -> list[dict[str, Any]]:
    return [
        {
            "id": f.id,
            "kind": f.kind,
            "subject": f.subject,
            "asset": f.asset,
            "tx_hash": f.tx_hash,
            "ledger_index": f.ledger_index,
            "evidence": f.evidence,
            "metrics": f.metrics,
            "status": f.status,
        }
        for f in store.findings(status)
    ]


@router.post("/findings/{finding_id}/dismiss")
def dismiss_finding(finding_id: int, user: AnalystDep, store: StoreDep) -> dict[str, bool]:
    store.set_finding_status(finding_id, "dismissed")
    return {"ok": True}


@router.post("/traces", status_code=202)
def create_trace(body: TraceIn, user: AnalystDep, store: StoreDep) -> dict[str, int]:
    return {"id": start_trace(store, user.id, body)}


@router.get("/traces/{trace_id}")
def get_trace(trace_id: int, user: AnalystDep, store: StoreDep) -> dict[str, Any]:
    row = store.trace(trace_id)
    if row is None:
        raise HTTPException(404, "no such trace")
    return {"id": row.id, "status": row.status, "error": row.error, "result": row.result}
