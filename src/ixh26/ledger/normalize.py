"""Raw validated XRPL transaction JSON (API v2) -> contract types. Pure: no network, no I/O."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from ixh26.contracts import (
    XRP,
    AccountActivity,
    Amount,
    Asset,
    PreTxBalance,
    SecurityEvent,
    SecurityEventKind,
    Transfer,
    TransferKind,
)

RIPPLE_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
ASF_DISABLE_MASTER = 4

Json = Mapping[str, Any]


class NormalizeError(ValueError):
    """The ledger returned something we cannot interpret safely."""


def parse_amount(raw: Any) -> Amount:
    """XRP amounts are strings of drops; issued amounts are {currency, issuer, value}."""
    if isinstance(raw, str):
        return Amount(XRP, Decimal(raw))
    if isinstance(raw, Mapping) and {"currency", "issuer", "value"} <= raw.keys():
        return Amount(Asset(raw["currency"], raw["issuer"]), Decimal(raw["value"]))
    raise NormalizeError(f"unsupported amount: {raw!r}")


def tx_body(entry: Json) -> Json:
    """``tx_json`` (API v2) or ``tx``/``transaction`` (API v1 and streams)."""
    for key in ("tx_json", "tx", "transaction"):
        if key in entry:
            return entry[key]
    raise NormalizeError("entry has no transaction body")


def _close_time(entry: Json, tx: Json) -> datetime:
    if iso := entry.get("close_time_iso"):
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if "date" in tx:
        return RIPPLE_EPOCH + timedelta(seconds=int(tx["date"]))
    raise NormalizeError("entry has no close time")


def _nodes(meta: Json, entry_type: str) -> list[tuple[str, Json]]:
    """(node kind, node body) for every affected ledger entry of ``entry_type``."""
    out = []
    for wrapper in meta.get("AffectedNodes", ()):
        (kind, node), *_ = wrapper.items()
        if node.get("LedgerEntryType") == entry_type:
            out.append((kind, node))
    return out


def _xrp_balances(meta: Json) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """(balance before the tx, balance delta) in drops for every touched AccountRoot."""
    before: dict[str, Decimal] = {}
    delta: dict[str, Decimal] = {}
    for kind, node in _nodes(meta, "AccountRoot"):
        if kind == "CreatedNode":
            fields = node["NewFields"]
            before[fields["Account"]] = Decimal(0)
            delta[fields["Account"]] = Decimal(fields.get("Balance", "0"))
            continue
        final = node.get("FinalFields", {})
        prev = node.get("PreviousFields", {})
        account = final.get("Account")
        if account is None or "Balance" not in final:
            continue
        old = Decimal(prev.get("Balance", final["Balance"]))
        new = Decimal(0) if kind == "DeletedNode" else Decimal(final["Balance"])
        before[account] = old
        delta[account] = new - old
    return before, delta


def _deleted_fields(meta: Json, entry_type: str) -> Json:
    for kind, node in _nodes(meta, entry_type):
        if kind == "DeletedNode":
            return node["FinalFields"]
    raise NormalizeError(f"no deleted {entry_type} in metadata")


def _delivered(meta: Json) -> Amount | None:
    raw = meta.get("delivered_amount", meta.get("DeliveredAmount"))
    if raw is None:
        return None
    if raw == "unavailable":  # pre-2014 ledgers only; never silently guess (CLAUDE.md §5)
        raise NormalizeError("delivered_amount unavailable")
    return parse_amount(raw)


@dataclass(frozen=True)
class TxContext:
    """One validated transaction, with what every extractor needs."""

    tx: Json
    meta: Json
    base: dict[str, Any]  # tx_hash, ledger_index, tx_index, close_time

    @property
    def fee(self) -> Decimal:
        return Decimal(self.tx.get("Fee", "0"))

    def xrp_delta(self, account: str) -> Decimal:
        return _xrp_balances(self.meta)[1].get(account, Decimal(0))

    def transfer(
        self, kind: TransferKind, src: str, dst: str, amount: Amount, **kw: Any
    ) -> Transfer:
        return Transfer(kind=kind, source=src, destination=dst, amount=amount, **self.base, **kw)


def _payment(c: TxContext) -> list[Transfer]:
    """Payments: always the delivered amount, so partial payments cannot lie."""
    amount = _delivered(c.meta)
    if amount is None:
        raise NormalizeError("payment without delivered_amount")
    src, dst = c.tx["Account"], c.tx["Destination"]
    paid_xrp = -(c.xrp_delta(src) + c.fee)
    source_amount = None
    if not amount.asset.is_xrp and paid_xrp > 0:
        source_amount = Amount(XRP, paid_xrp)  # cross-currency payment funded with XRP
    return [
        c.transfer(
            TransferKind.PAYMENT,
            src,
            dst,
            amount,
            destination_tag=c.tx.get("DestinationTag"),
            source_amount=source_amount,
        )
    ]


def _account_delete(c: TxContext) -> list[Transfer]:
    """Deleting an account sends its remaining XRP to the destination."""
    dst = c.tx["Destination"]
    amount = _delivered(c.meta) or Amount(XRP, c.xrp_delta(dst))
    kind = TransferKind.ACCOUNT_DELETE
    return [
        c.transfer(kind, c.tx["Account"], dst, amount, destination_tag=c.tx.get("DestinationTag"))
    ]


def _check_cash(c: TxContext) -> list[Transfer]:
    """The check's writer pays the casher."""
    writer = _deleted_fields(c.meta, "Check")["Account"]
    casher = c.tx["Account"]
    amount = _delivered(c.meta) or Amount(XRP, c.xrp_delta(casher) + c.fee)
    return [c.transfer(TransferKind.CHECK_CASH, writer, casher, amount)]


def _escrow_finish(c: TxContext) -> list[Transfer]:
    """Escrowed XRP moves from the escrow owner to its destination."""
    escrow = _deleted_fields(c.meta, "Escrow")
    return [
        c.transfer(
            TransferKind.ESCROW_FINISH,
            escrow["Account"],
            escrow["Destination"],
            parse_amount(escrow["Amount"]),
            destination_tag=escrow.get("DestinationTag"),
        )
    ]


def _channel_claim(c: TxContext) -> list[Transfer]:
    """A channel claim pays the increase of the channel's Balance field."""
    for _, node in _nodes(c.meta, "PayChannel"):
        final, prev = node.get("FinalFields", {}), node.get("PreviousFields", {})
        if "Balance" in prev:
            paid = Decimal(final["Balance"]) - Decimal(prev["Balance"])
            return [
                c.transfer(
                    TransferKind.CHANNEL_CLAIM,
                    final["Account"],
                    final["Destination"],
                    Amount(XRP, paid),
                    destination_tag=final.get("DestinationTag"),
                )
            ]
    return []


# Transaction type -> how value moved. Types not listed here move no value we trace.
EXTRACTORS: dict[str, Callable[[TxContext], list[Transfer]]] = {
    "Payment": _payment,
    "AccountDelete": _account_delete,
    "CheckCash": _check_cash,
    "EscrowFinish": _escrow_finish,
    "PaymentChannelClaim": _channel_claim,
}


def _transfers(c: TxContext) -> list[Transfer]:
    extractor = EXTRACTORS.get(c.tx["TransactionType"])
    return extractor(c) if extractor else []


def _security_events(tx: Json, base: dict[str, Any]) -> list[SecurityEvent]:
    kind = tx["TransactionType"]
    account = tx["Account"]
    event = None
    if kind == "SetRegularKey":
        event = (SecurityEventKind.SET_REGULAR_KEY, tx.get("RegularKey", "removed"))
    elif kind == "SignerListSet":
        event = (SecurityEventKind.SIGNER_LIST_SET, f"quorum={tx.get('SignerQuorum', 0)}")
    elif kind == "AccountSet" and tx.get("SetFlag") == ASF_DISABLE_MASTER:
        event = (SecurityEventKind.MASTER_KEY_DISABLED, "")
    elif kind == "AccountDelete":
        event = (SecurityEventKind.ACCOUNT_DELETE, tx["Destination"])
    if event is None:
        return []
    return [
        SecurityEvent(
            tx_hash=base["tx_hash"],
            ledger_index=base["ledger_index"],
            close_time=base["close_time"],
            account=account,
            kind=event[0],
            detail=event[1],
            tx_index=base["tx_index"],
        )
    ]


def normalize(entry: Json) -> AccountActivity:
    """Extract transfers, security events and senders' pre-tx balances from one tx.

    Only validated ``tesSUCCESS`` transactions produce anything.
    """
    tx = tx_body(entry)
    meta = entry.get("meta") or entry.get("metaData") or {}
    if not entry.get("validated", False) or meta.get("TransactionResult") != "tesSUCCESS":
        return AccountActivity()
    base = {
        "tx_hash": entry.get("hash") or tx["hash"],
        "ledger_index": int(entry.get("ledger_index") or tx["ledger_index"]),
        "tx_index": int(meta["TransactionIndex"]),
        "close_time": _close_time(entry, tx),
    }
    transfers = _transfers(TxContext(tx, meta, base))
    before, _ = _xrp_balances(meta)
    # shortcut: pre-tx balances only for XRP senders; add RippleState balances for IOU takeovers
    balances = tuple(
        PreTxBalance(base["tx_hash"], t.source, Amount(XRP, before[t.source]))
        for t in transfers
        if (t.source_amount or t.amount).asset.is_xrp and t.source in before
    )
    security = _security_events(tx, base)
    return AccountActivity(tuple(transfers), tuple(security), balances)
