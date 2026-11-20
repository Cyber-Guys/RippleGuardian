"""Normalisation of raw ledger JSON. The XRP payment fixture is a real Testnet tx; the others
are hand-built from the documented metadata shape (test inputs only, never shown as evidence)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ixh26.contracts import XRP, Asset, SecurityEventKind, TransferKind
from ixh26.ledger.normalize import NormalizeError, normalize

FIXTURES = Path(__file__).parent / "fixtures"
H = "AB" * 32


def _entry(tx: dict, meta: dict, **extra: object) -> dict:
    meta = {"TransactionIndex": 3, "TransactionResult": "tesSUCCESS", **meta}
    return {
        "hash": H,
        "ledger_index": 100,
        "close_time_iso": "2026-11-20T22:00:00Z",
        "validated": True,
        "tx_json": {"Fee": "12", **tx},
        "meta": meta,
        **extra,
    }


def _root(account: str, before: str, after: str) -> dict:
    return {
        "ModifiedNode": {
            "LedgerEntryType": "AccountRoot",
            "FinalFields": {"Account": account, "Balance": after},
            "PreviousFields": {"Balance": before},
        }
    }


def test_real_testnet_xrp_payment_uses_delivered_amount() -> None:
    entry = json.loads((FIXTURES / "testnet_xrp_payment.json").read_text())
    activity = normalize(entry)
    (t,) = activity.transfers
    assert t.kind is TransferKind.PAYMENT
    assert t.amount.asset == XRP and t.amount.value == Decimal(1200024)
    assert t.source == entry["tx_json"]["Account"]
    assert t.order_key == (entry["ledger_index"], 7)
    (bal,) = activity.pre_tx_balances
    assert bal.account == t.source and bal.amount.value == Decimal(224792140)


def test_partial_payment_reports_delivered_not_requested_amount() -> None:
    iou = {"currency": "USD", "issuer": "rIssuer", "value": "5"}
    tx = {
        "TransactionType": "Payment",
        "Account": "rA",
        "Destination": "rB",
        "DestinationTag": 42,
        "DeliverMax": {**iou, "value": "1000"},
        "Flags": 131072,
    }
    (t,) = normalize(_entry(tx, {"delivered_amount": iou})).transfers
    assert t.amount.asset == Asset("USD", "rIssuer")
    assert t.amount.value == Decimal(5)
    assert t.destination_tag == 42


def test_failed_or_unvalidated_txs_produce_nothing() -> None:
    tx = {"TransactionType": "Payment", "Account": "rA", "Destination": "rB"}
    failed = _entry(tx, {"TransactionResult": "tecPATH_DRY"})
    pending = _entry(tx, {"delivered_amount": "5"}, validated=False)
    assert normalize(failed).transfers == ()
    assert normalize(pending).transfers == ()


def test_unavailable_delivered_amount_fails_loudly() -> None:
    tx = {"TransactionType": "Payment", "Account": "rA", "Destination": "rB"}
    with pytest.raises(NormalizeError):
        normalize(_entry(tx, {"delivered_amount": "unavailable"}))


@pytest.mark.parametrize(
    ("tx", "kind", "detail"),
    [
        ({"TransactionType": "SetRegularKey", "RegularKey": "rK"}, "set_regular_key", "rK"),
        ({"TransactionType": "SignerListSet", "SignerQuorum": 2}, "signer_list_set", "quorum=2"),
        ({"TransactionType": "AccountSet", "SetFlag": 4}, "master_key_disabled", ""),
    ],
)
def test_signing_changes_are_security_events(tx: dict, kind: str, detail: str) -> None:
    (event,) = normalize(_entry({"Account": "rA", **tx}, {})).security_events
    assert event.kind is SecurityEventKind(kind)
    assert event.detail == detail
    assert event.tx_index == 3


def test_account_delete_is_transfer_and_security_event() -> None:
    tx = {"TransactionType": "AccountDelete", "Account": "rA", "Destination": "rX"}
    meta = {
        "delivered_amount": "9000000",
        "AffectedNodes": [_root("rX", "1000", "9001000")],
    }
    activity = normalize(_entry(tx, meta))
    assert activity.transfers[0].kind is TransferKind.ACCOUNT_DELETE
    assert activity.transfers[0].amount.value == Decimal(9000000)
    assert activity.security_events[0].kind is SecurityEventKind.ACCOUNT_DELETE


def test_escrow_finish_check_cash_and_channel_claim() -> None:
    escrow = _entry(
        {"TransactionType": "EscrowFinish", "Account": "rZ", "Owner": "rA"},
        {
            "AffectedNodes": [
                {
                    "DeletedNode": {
                        "LedgerEntryType": "Escrow",
                        "FinalFields": {"Account": "rA", "Destination": "rB", "Amount": "700"},
                    }
                }
            ]
        },
    )
    check = _entry(
        {"TransactionType": "CheckCash", "Account": "rB"},
        {
            "AffectedNodes": [
                {"DeletedNode": {"LedgerEntryType": "Check", "FinalFields": {"Account": "rA"}}},
                _root("rB", "1000", "1488"),
            ]
        },
    )
    claim = _entry(
        {"TransactionType": "PaymentChannelClaim", "Account": "rB"},
        {
            "AffectedNodes": [
                {
                    "ModifiedNode": {
                        "LedgerEntryType": "PayChannel",
                        "FinalFields": {"Account": "rA", "Destination": "rB", "Balance": "900"},
                        "PreviousFields": {"Balance": "400"},
                    }
                }
            ]
        },
    )
    (e,) = normalize(escrow).transfers
    (c,) = normalize(check).transfers
    (p,) = normalize(claim).transfers
    assert (e.kind, e.source, e.destination, e.amount.value) == (
        TransferKind.ESCROW_FINISH,
        "rA",
        "rB",
        Decimal(700),
    )
    assert (c.source, c.destination, c.amount.value) == ("rA", "rB", Decimal(500))
    assert (p.kind, p.amount.value) == (TransferKind.CHANNEL_CLAIM, Decimal(500))
