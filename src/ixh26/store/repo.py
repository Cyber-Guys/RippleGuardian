"""Persistence API used by app/ and flows/. Imports neither ledger/ nor xrpl (D-004).

shortcut: synchronous SQLAlchemy sessions, also called from the async worker; fine at demo
scale, switch to the async engine if the worker ever watches thousands of wallets.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, delete, func, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ixh26.contracts import (
    XRP,
    AccountActivity,
    AccountLabel,
    AccountLabelKind,
    Alert,
    Amount,
    Asset,
    PreTxBalance,
    SecurityEvent,
    SecurityEventKind,
    Transfer,
    TransferKind,
)
from ixh26.store.models import (
    AlertRow,
    BalanceRow,
    Base,
    Cursor,
    FindingRow,
    FlagRow,
    LabelRow,
    SecurityEventRow,
    TraceRow,
    TransferRow,
    User,
    Wallet,
)

ROLES = ("user", "analyst")


def aware(dt: datetime) -> datetime:
    """SQLite drops tzinfo; every datetime we store is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def asset_of(currency: str, issuer: str | None) -> Asset:
    return XRP if currency == "XRP" else Asset(currency, issuer or None)


def _issuer(asset: Asset) -> str:
    return asset.issuer or ""


def to_transfer(row: TransferRow) -> Transfer:
    source_amount = None
    if row.source_currency is not None and row.source_value is not None:
        source_amount = Amount(
            asset_of(row.source_currency, row.source_issuer), Decimal(row.source_value)
        )
    return Transfer(
        tx_hash=row.tx_hash,
        ledger_index=row.ledger_index,
        tx_index=row.tx_index,
        close_time=aware(row.close_time),
        kind=TransferKind(row.kind),
        source=row.source,
        destination=row.destination,
        amount=Amount(asset_of(row.currency, row.issuer), Decimal(row.value)),
        destination_tag=row.destination_tag,
        source_amount=source_amount,
    )


def to_event(row: SecurityEventRow) -> SecurityEvent:
    return SecurityEvent(
        tx_hash=row.tx_hash,
        ledger_index=row.ledger_index,
        close_time=aware(row.close_time),
        account=row.account,
        kind=SecurityEventKind(row.kind),
        detail=row.detail,
        tx_index=row.tx_index,
    )


@dataclass(frozen=True)
class FindingInput:
    """Detector output flattened for storage (flows/ converts core findings to this)."""

    kind: str
    subject: str
    asset: str
    tx_hash: str
    ledger_index: int
    close_time: datetime
    evidence: tuple[str, ...]
    metrics: dict[str, str]


class Store:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session = sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def from_url(cls, url: str) -> Store:
        kwargs: dict[str, Any] = {}
        if url == "sqlite://" or (url.startswith("sqlite") and ":memory:" in url):
            kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        elif url.startswith("sqlite"):
            kwargs = {"connect_args": {"check_same_thread": False}}
        store = cls(create_engine(url, **kwargs))
        Base.metadata.create_all(store.engine)  # shortcut: no migrations; add Alembic later
        return store

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session() as s, s.begin():
            yield s

    # --- users ------------------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str, role: str = "user") -> User:
        if role not in ROLES:
            raise ValueError(f"unknown role {role!r}")
        with self.session() as s:
            user = User(username=username, password_hash=password_hash, role=role)
            s.add(user)
            s.flush()
            return user

    def user_by_name(self, username: str) -> User | None:
        with self.session() as s:
            return s.scalar(select(User).where(User.username == username))

    def user(self, user_id: int) -> User | None:
        with self.session() as s:
            return s.get(User, user_id)

    # --- wallets ----------------------------------------------------------------------------

    def add_wallet(self, user_id: int, address: str, label: str = "") -> Wallet:
        with self.session() as s:
            wallet = Wallet(user_id=user_id, address=address, label=label)
            s.add(wallet)
            s.flush()
            return wallet

    def wallets(self, user_id: int) -> list[Wallet]:
        with self.session() as s:
            return list(s.scalars(select(Wallet).where(Wallet.user_id == user_id)))

    def wallet(self, user_id: int, address: str) -> Wallet | None:
        with self.session() as s:
            return s.scalar(
                select(Wallet).where(Wallet.user_id == user_id, Wallet.address == address)
            )

    def update_wallet(self, user_id: int, address: str, **fields: Any) -> None:
        allowed = {
            "label",
            "notify_outgoing",
            "notify_security",
            "notify_flagged",
            "min_outgoing_drops",
        }
        if not fields.keys() <= allowed:
            raise ValueError(f"cannot update {sorted(fields.keys() - allowed)}")
        with self.session() as s:
            s.execute(
                update(Wallet)
                .where(Wallet.user_id == user_id, Wallet.address == address)
                .values(**fields)
            )

    def remove_wallet(self, user_id: int, address: str) -> None:
        with self.session() as s:
            s.execute(delete(Wallet).where(Wallet.user_id == user_id, Wallet.address == address))

    def watched_addresses(self) -> list[str]:
        with self.session() as s:
            return list(s.scalars(select(Wallet.address).distinct()))

    def watchers(self, address: str) -> list[Wallet]:
        with self.session() as s:
            return list(s.scalars(select(Wallet).where(Wallet.address == address)))

    def cursor(self, address: str) -> int | None:
        with self.session() as s:
            row = s.get(Cursor, address)
            return row.ledger_index if row else None

    def set_cursor(self, address: str, ledger_index: int) -> None:
        with self.session() as s:
            row = s.get(Cursor, address)
            if row is None:
                s.add(Cursor(address=address, ledger_index=ledger_index))
            elif ledger_index > row.ledger_index:
                row.ledger_index = ledger_index

    # --- ledger activity ----------------------------------------------------------------------

    def save_activity(
        self, activity: AccountActivity
    ) -> tuple[list[Transfer], list[SecurityEvent]]:
        """Insert what is new; return only the new transfers/events (idempotent)."""
        new_t: list[Transfer] = []
        new_e: list[SecurityEvent] = []
        with self.session() as s:
            for t in activity.transfers:
                if _exists(
                    s,
                    TransferRow,
                    tx_hash=t.tx_hash,
                    source=t.source,
                    destination=t.destination,
                    currency=t.amount.asset.currency,
                    issuer=_issuer(t.amount.asset),
                ):
                    continue
                sa = t.source_amount
                s.add(
                    TransferRow(
                        tx_hash=t.tx_hash,
                        ledger_index=t.ledger_index,
                        tx_index=t.tx_index,
                        close_time=t.close_time,
                        kind=t.kind.value,
                        source=t.source,
                        destination=t.destination,
                        destination_tag=t.destination_tag,
                        currency=t.amount.asset.currency,
                        issuer=_issuer(t.amount.asset),
                        value=str(t.amount.value),
                        source_currency=sa.asset.currency if sa else None,
                        source_issuer=_issuer(sa.asset) if sa else None,
                        source_value=str(sa.value) if sa else None,
                    )
                )
                new_t.append(t)
            for e in activity.security_events:
                if _exists(s, SecurityEventRow, tx_hash=e.tx_hash, kind=e.kind.value):
                    continue
                s.add(
                    SecurityEventRow(
                        tx_hash=e.tx_hash,
                        ledger_index=e.ledger_index,
                        tx_index=e.tx_index,
                        close_time=e.close_time,
                        account=e.account,
                        kind=e.kind.value,
                        detail=e.detail[:80],
                    )
                )
                new_e.append(e)
            for b in activity.pre_tx_balances:
                key = {
                    "tx_hash": b.tx_hash,
                    "account": b.account,
                    "currency": b.amount.asset.currency,
                    "issuer": _issuer(b.amount.asset),
                }
                if not _exists(s, BalanceRow, **key):
                    s.add(BalanceRow(**key, value=str(b.amount.value)))
        return new_t, new_e

    def transfers_of(
        self, addresses: Iterable[str], *, since: datetime | None = None, limit: int = 5000
    ) -> list[Transfer]:
        addresses = list(addresses)
        with self.session() as s:
            q = select(TransferRow).where(
                or_(TransferRow.source.in_(addresses), TransferRow.destination.in_(addresses))
            )
            if since is not None:
                q = q.where(TransferRow.close_time >= since)
            q = q.order_by(TransferRow.ledger_index.desc(), TransferRow.tx_index.desc())
            return [to_transfer(r) for r in s.scalars(q.limit(limit))][::-1]

    def events_of(self, addresses: Iterable[str], *, limit: int = 500) -> list[SecurityEvent]:
        with self.session() as s:
            q = (
                select(SecurityEventRow)
                .where(SecurityEventRow.account.in_(list(addresses)))
                .order_by(SecurityEventRow.ledger_index.desc())
                .limit(limit)
            )
            return [to_event(r) for r in s.scalars(q)][::-1]

    def balances_for(self, tx_hashes: Iterable[str]) -> list[PreTxBalance]:
        with self.session() as s:
            rows = s.scalars(select(BalanceRow).where(BalanceRow.tx_hash.in_(list(tx_hashes))))
            return [
                PreTxBalance(
                    r.tx_hash, r.account, Amount(asset_of(r.currency, r.issuer), Decimal(r.value))
                )
                for r in rows
            ]

    # --- alerts -----------------------------------------------------------------------------

    def add_alert(self, user_id: int, alert: Alert) -> bool:
        with self.session() as s:
            if _exists(
                s,
                AlertRow,
                user_id=user_id,
                wallet=alert.wallet,
                kind=alert.kind.value,
                tx_hash=alert.tx_hash,
            ):
                return False
            s.add(
                AlertRow(
                    user_id=user_id,
                    wallet=alert.wallet,
                    kind=alert.kind.value,
                    severity=alert.severity.value,
                    tx_hash=alert.tx_hash,
                    message=alert.message[:280],
                    created_at=alert.created_at,
                )
            )
            return True

    def alerts(
        self, user_id: int, *, unread_only: bool = False, limit: int = 100
    ) -> list[AlertRow]:
        with self.session() as s:
            q = select(AlertRow).where(AlertRow.user_id == user_id)
            if unread_only:
                q = q.where(AlertRow.read.is_(False))
            return list(s.scalars(q.order_by(AlertRow.id.desc()).limit(limit)))

    def unread_count(self, user_id: int) -> int:
        with self.session() as s:
            return (
                s.scalar(
                    select(func.count())
                    .select_from(AlertRow)
                    .where(AlertRow.user_id == user_id, AlertRow.read.is_(False))
                )
                or 0
            )

    def mark_read(self, user_id: int, alert_ids: Sequence[int] | None = None) -> None:
        with self.session() as s:
            q = update(AlertRow).where(AlertRow.user_id == user_id)
            if alert_ids is not None:
                q = q.where(AlertRow.id.in_(list(alert_ids)))
            s.execute(q.values(read=True))

    # --- findings ---------------------------------------------------------------------------

    def add_finding(self, f: FindingInput) -> bool:
        with self.session() as s:
            if _exists(s, FindingRow, kind=f.kind, subject=f.subject, tx_hash=f.tx_hash):
                return False
            s.add(
                FindingRow(
                    kind=f.kind,
                    subject=f.subject,
                    asset=f.asset,
                    tx_hash=f.tx_hash,
                    ledger_index=f.ledger_index,
                    close_time=f.close_time,
                    evidence=list(f.evidence),
                    metrics=dict(f.metrics),
                )
            )
            return True

    def findings(self, status: str | None = None, limit: int = 200) -> list[FindingRow]:
        with self.session() as s:
            q = select(FindingRow)
            if status:
                q = q.where(FindingRow.status == status)
            return list(s.scalars(q.order_by(FindingRow.id.desc()).limit(limit)))

    def finding(self, finding_id: int) -> FindingRow | None:
        with self.session() as s:
            return s.get(FindingRow, finding_id)

    def set_finding_status(self, finding_id: int, status: str) -> None:
        if status not in ("open", "flagged", "dismissed"):
            raise ValueError(f"unknown finding status {status!r}")
        with self.session() as s:
            s.execute(update(FindingRow).where(FindingRow.id == finding_id).values(status=status))

    # --- flags ------------------------------------------------------------------------------

    def add_flag(
        self,
        target_type: str,
        target: str,
        category: str,
        reason: str,
        analyst_id: int,
        finding_id: int | None = None,
    ) -> FlagRow:
        if target_type not in ("account", "tx"):
            raise ValueError("target_type must be 'account' or 'tx'")
        with self.session() as s:
            flag = FlagRow(
                target_type=target_type,
                target=target,
                category=category,
                reason=reason[:280],
                analyst_id=analyst_id,
                finding_id=finding_id,
            )
            s.add(flag)
            s.flush()
            return flag

    def revoke_flag(self, flag_id: int) -> None:
        with self.session() as s:
            s.execute(update(FlagRow).where(FlagRow.id == flag_id).values(active=False))

    def flags(self, *, active_only: bool = True) -> list[tuple[FlagRow, str]]:
        """(flag, analyst username), newest first."""
        with self.session() as s:
            q = select(FlagRow, User.username).join(User, User.id == FlagRow.analyst_id)
            if active_only:
                q = q.where(FlagRow.active.is_(True))
            return [(f, name) for f, name in s.execute(q.order_by(FlagRow.id.desc()))]

    def flagged_targets(self) -> dict[str, FlagRow]:
        """Active flags by target (address or tx hash); newest flag wins."""
        return {f.target: f for f, _ in reversed(self.flags())}

    # --- labels -----------------------------------------------------------------------------

    def upsert_label(self, label: AccountLabel) -> None:
        with self.session() as s:
            row = s.get(LabelRow, label.address)
            if row is None:
                s.add(LabelRow(address=label.address, kind=label.kind.value, name=label.name))
            else:
                row.kind, row.name = label.kind.value, label.name

    def labels(self) -> dict[str, AccountLabel]:
        with self.session() as s:
            return {
                r.address: AccountLabel(r.address, AccountLabelKind(r.kind), r.name)
                for r in s.scalars(select(LabelRow))
            }

    # --- traces -----------------------------------------------------------------------------

    def create_trace(
        self,
        analyst_id: int,
        origin: str,
        asset: Asset,
        stolen_value: Decimal,
        start_ledger: int,
    ) -> TraceRow:
        with self.session() as s:
            row = TraceRow(
                analyst_id=analyst_id,
                origin=origin,
                currency=asset.currency,
                issuer=_issuer(asset),
                stolen_value=str(stolen_value),
                start_ledger=start_ledger,
            )
            s.add(row)
            s.flush()
            return row

    def traces(self, limit: int = 50) -> list[TraceRow]:
        with self.session() as s:
            return list(s.scalars(select(TraceRow).order_by(TraceRow.id.desc()).limit(limit)))

    def trace(self, trace_id: int) -> TraceRow | None:
        with self.session() as s:
            return s.get(TraceRow, trace_id)

    def pending_traces(self) -> list[TraceRow]:
        with self.session() as s:
            return list(s.scalars(select(TraceRow).where(TraceRow.status == "pending")))

    def finish_trace(
        self, trace_id: int, *, result: dict[str, Any] | None = None, error: str = ""
    ) -> None:
        with self.session() as s:
            s.execute(
                update(TraceRow)
                .where(TraceRow.id == trace_id)
                .values(status="failed" if error else "done", result=result, error=error[:280])
            )


def _exists(s: Session, model: type[Base], **where: Any) -> bool:
    q = select(model).filter_by(**where).limit(1)
    return s.scalar(q) is not None
