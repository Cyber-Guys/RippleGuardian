"""SQLAlchemy tables. Amounts are stored as exact decimal strings, never floats."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map: ClassVar = {dict[str, Any]: JSON, list[Any]: JSON}


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # user | analyst
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Wallet(Base):
    """A watched address. Several users may watch the same address."""

    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id", "address"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    address: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str] = mapped_column(String(40), default="")
    notify_outgoing: Mapped[bool] = mapped_column(default=True)
    notify_security: Mapped[bool] = mapped_column(default=True)
    notify_flagged: Mapped[bool] = mapped_column(default=True)
    min_outgoing_drops: Mapped[str] = mapped_column(String(40), default="0")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class WalletChallenge(Base):
    """A payment challenge bound to this particular watch, even after it is deleted."""

    __tablename__ = "wallet_challenges"
    __table_args__ = (
        UniqueConstraint("network", "destination", "destination_tag"),
        UniqueConstraint("network", "payment_hash"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    wallet_id: Mapped[int] = mapped_column(index=True)
    wallet_created_at: Mapped[datetime]
    network: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str] = mapped_column(String(40))
    destination_tag: Mapped[int] = mapped_column(BigInteger)
    after_ledger: Mapped[int]
    expires_at: Mapped[datetime]
    payment_hash: Mapped[str | None] = mapped_column(String(64))
    verified_at: Mapped[datetime | None]


class Cursor(Base):
    """Last ledger fully processed for an address (worker catch-up point)."""

    __tablename__ = "cursors"
    address: Mapped[str] = mapped_column(String(40), primary_key=True)
    ledger_index: Mapped[int]


class TransferRow(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("tx_hash", "source", "destination", "currency", "issuer"),
        Index("ix_transfers_time", "ledger_index", "tx_index"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(64), index=True)
    ledger_index: Mapped[int]
    tx_index: Mapped[int]
    close_time: Mapped[datetime]
    kind: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(40), index=True)
    destination: Mapped[str] = mapped_column(String(40), index=True)
    destination_tag: Mapped[int | None]
    currency: Mapped[str] = mapped_column(String(40))
    issuer: Mapped[str] = mapped_column(String(40), default="")
    value: Mapped[str] = mapped_column(String(40))
    source_currency: Mapped[str | None] = mapped_column(String(40))
    source_issuer: Mapped[str | None] = mapped_column(String(40))
    source_value: Mapped[str | None] = mapped_column(String(40))


class SecurityEventRow(Base):
    __tablename__ = "security_events"
    __table_args__ = (UniqueConstraint("tx_hash", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(64))
    ledger_index: Mapped[int]
    tx_index: Mapped[int]
    close_time: Mapped[datetime]
    account: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    detail: Mapped[str] = mapped_column(String(80), default="")


class BalanceRow(Base):
    """Sender balance right before a tx (from metadata); feeds the takeover detector."""

    __tablename__ = "pre_tx_balances"
    __table_args__ = (UniqueConstraint("tx_hash", "account", "currency", "issuer"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(64), index=True)
    account: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(40))
    issuer: Mapped[str] = mapped_column(String(40), default="")
    value: Mapped[str] = mapped_column(String(40))


class AlertRow(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("user_id", "wallet", "kind", "tx_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    wallet: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    tx_hash: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(280))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    read: Mapped[bool] = mapped_column(default=False)


class FindingRow(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("kind", "subject", "tx_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(60), index=True)
    asset: Mapped[str] = mapped_column(String(90))
    tx_hash: Mapped[str] = mapped_column(String(64))
    ledger_index: Mapped[int]
    close_time: Mapped[datetime]
    evidence: Mapped[list[Any]]
    metrics: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | flagged | dismissed
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class FlagRow(Base):
    """An analyst's public, accountable statement that an account or tx is suspicious."""

    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(8))  # account | tx
    target: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(280))
    analyst_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LabelRow(Base):
    __tablename__ = "labels"
    address: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(60))


class TraceRow(Base):
    __tablename__ = "traces"
    id: Mapped[int] = mapped_column(primary_key=True)
    analyst_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    origin: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(40))
    issuer: Mapped[str] = mapped_column(String(40), default="")
    stolen_value: Mapped[str] = mapped_column(String(40))
    start_ledger: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|done|failed
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str] = mapped_column(String(280), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
