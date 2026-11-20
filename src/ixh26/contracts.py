"""Shared, frozen data types and Protocols between modules (CLAUDE.md §4).

Changing this file requires its own small contract task. Rules baked in here:
- amounts are ``Decimal`` only; XRP is always expressed in **drops** (integral Decimal),
  IOU tokens in their native decimal units;
- a ``Transfer`` always carries the *delivered* amount, never the requested ``Amount``;
- nothing here imports ``xrpl``: ``ledger/`` converts raw ledger JSON into these types.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

XRP_CURRENCY = "XRP"


@dataclass(frozen=True, order=True)
class Asset:
    """XRP (``issuer is None``) or an issued token identified by currency + issuer."""

    currency: str
    issuer: str | None = None

    def __post_init__(self) -> None:
        if (self.currency == XRP_CURRENCY) != (self.issuer is None):
            raise ValueError("XRP has no issuer; every other currency needs one")

    @property
    def is_xrp(self) -> bool:
        return self.issuer is None

    def __str__(self) -> str:
        return XRP_CURRENCY if self.is_xrp else f"{self.currency}.{self.issuer}"


XRP = Asset(XRP_CURRENCY)


@dataclass(frozen=True)
class Amount:
    asset: Asset
    value: Decimal  # drops for XRP, token units otherwise

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Amount.value must be Decimal (never float)")
        if self.asset.is_xrp and self.value != self.value.to_integral_value():
            raise ValueError("XRP amounts are integer drops")


class TransferKind(StrEnum):
    """How value moved. Every kind is an edge in the funds graph."""

    PAYMENT = "payment"
    ACCOUNT_DELETE = "account_delete"
    CHECK_CASH = "check_cash"
    ESCROW_FINISH = "escrow_finish"
    CHANNEL_CLAIM = "channel_claim"
    DEX_TRADE = "dex_trade"  # OfferCreate / AMM swap: value changes asset within an account


@dataclass(frozen=True)
class Transfer:
    """One validated, successful movement of value from ``source`` to ``destination``."""

    tx_hash: str
    ledger_index: int
    tx_index: int  # position inside the ledger: (ledger_index, tx_index) is a total order
    close_time: datetime
    kind: TransferKind
    source: str
    destination: str
    amount: Amount  # delivered amount (meta.delivered_amount / balance deltas)
    destination_tag: int | None = None
    source_amount: Amount | None = None  # what left ``source`` if different asset (DEX/paths)

    @property
    def order_key(self) -> tuple[int, int]:
        return (self.ledger_index, self.tx_index)


class SecurityEventKind(StrEnum):
    """Account-control changes that usually precede or accompany a theft."""

    SET_REGULAR_KEY = "set_regular_key"
    SIGNER_LIST_SET = "signer_list_set"
    MASTER_KEY_DISABLED = "master_key_disabled"
    ACCOUNT_DELETE = "account_delete"


@dataclass(frozen=True)
class SecurityEvent:
    tx_hash: str
    ledger_index: int
    close_time: datetime
    account: str
    kind: SecurityEventKind
    detail: str = ""  # short, non-sensitive (e.g. the new regular key address)


@dataclass(frozen=True)
class AccountActivity:
    """Everything ``ledger/`` extracted from one transaction for one watched account."""

    transfers: tuple[Transfer, ...] = ()
    security_events: tuple[SecurityEvent, ...] = ()


# --- Taint tracking ---------------------------------------------------------------------------


class TaintModel(StrEnum):
    HAIRCUT = "haircut"  # implemented; POISON / FIFO are roadmap


@dataclass(frozen=True)
class TraceParams:
    origin: str  # the compromised account
    asset: Asset
    stolen_value: Decimal  # amount that left the victim illegitimately
    start_ledger: int  # only activity from this ledger on is considered
    min_ratio: Decimal = Decimal("0.01")  # stop below 1% of the stolen amount
    min_value: Decimal = Decimal(1_000_000)  # ...or below this absolute value (1 XRP)
    max_hops: int = 6
    model: TaintModel = TaintModel.HAIRCUT


@dataclass(frozen=True)
class TaintEdge:
    transfer: Transfer
    hop: int  # 1 = directly out of the origin
    taint_value: Decimal  # stolen value carried by this transfer (same unit as amount)
    taint_ratio: Decimal  # taint_value / transfer.amount.value, in [0, 1]


class AccountLabelKind(StrEnum):
    EXCHANGE = "exchange"
    ISSUER = "issuer"
    BRIDGE = "bridge"
    MIXER = "mixer"
    REPORTED = "reported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AccountLabel:
    address: str
    kind: AccountLabelKind
    name: str


@dataclass(frozen=True)
class TaintSink:
    """Where tainted value currently rests (or was handed to a labelled entity)."""

    address: str
    destination_tag: int | None
    taint_value: Decimal
    hop: int
    label: AccountLabel | None = None


@dataclass(frozen=True)
class TraceResult:
    params: TraceParams
    edges: tuple[TaintEdge, ...]
    sinks: tuple[TaintSink, ...]
    truncated: bool  # True if max_hops or the threshold cut the graph
    computed_at: datetime
    disclaimer: str = "Heuristic attribution: results are probable, not certain."


# --- Alerts -----------------------------------------------------------------------------------


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertKind(StrEnum):
    OUTGOING_PAYMENT = "outgoing_payment"
    SECURITY_CHANGE = "security_change"
    TAINT_AT_EXCHANGE = "taint_at_exchange"
    TAINTED_TOKEN_MOVED = "tainted_token_moved"  # notify the issuer (freeze / clawback)


@dataclass(frozen=True)
class Alert:
    wallet: str
    kind: AlertKind
    severity: AlertSeverity
    tx_hash: str
    message: str
    created_at: datetime


# --- XRPL write path (submit helper in ledger/client.py) ---------------------------------------


@dataclass(frozen=True)
class TxResult:
    """Result of a validated tesSUCCESS submission; anything else raises."""

    tx_hash: str
    tx_type: str
    network: str
    ledger_index: int
    purpose: str
    explorer_url: str
    submitted_at: datetime
    meta: dict[str, object] = field(default_factory=dict, compare=False, repr=False)


# --- Protocols (implemented by ledger/ and store/, consumed by core/ and flows/) ---------------


class LedgerReader(Protocol):
    """Read side of the ledger. Implementations live in ``ledger/``; tests inject fakes."""

    async def account_activity(
        self, account: str, *, from_ledger: int, to_ledger: int | None = None
    ) -> Sequence[AccountActivity]: ...

    async def current_ledger(self) -> int: ...


class LedgerStream(Protocol):
    """Live stream of validated activity for a dynamic set of accounts."""

    def watch(self, accounts: Sequence[str]) -> AsyncIterator[AccountActivity]: ...
