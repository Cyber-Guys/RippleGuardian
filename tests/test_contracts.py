import dataclasses
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ixh26.contracts import XRP, Amount, Asset, TraceParams, Transfer, TransferKind


def _transfer(ledger: int, idx: int) -> Transfer:
    return Transfer(
        tx_hash=f"{ledger:032d}{idx:032d}",
        ledger_index=ledger,
        tx_index=idx,
        close_time=datetime(2026, 11, 20, tzinfo=UTC),
        kind=TransferKind.PAYMENT,
        source="rA",
        destination="rB",
        amount=Amount(XRP, Decimal(5_000_000)),
    )


def test_float_amounts_are_rejected() -> None:
    with pytest.raises(TypeError):
        Amount(XRP, 1.5)  # type: ignore[arg-type]


def test_xrp_amounts_are_integer_drops() -> None:
    with pytest.raises(ValueError):
        Amount(XRP, Decimal("1.5"))
    Amount(Asset("USD", "rIssuer"), Decimal("1.5"))  # tokens may be fractional


def test_asset_issuer_consistency() -> None:
    with pytest.raises(ValueError):
        Asset("XRP", "rIssuer")
    with pytest.raises(ValueError):
        Asset("USD")
    assert str(Asset("USD", "rI")) == "USD.rI"


def test_transfers_are_frozen_and_totally_ordered() -> None:
    a, b, c = _transfer(10, 5), _transfer(11, 0), _transfer(10, 6)
    assert sorted([b, c, a], key=lambda t: t.order_key) == [a, c, b]
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.ledger_index = 3  # type: ignore[misc]


def test_trace_defaults_match_policy() -> None:
    p = TraceParams(origin="rV", asset=XRP, stolen_value=Decimal(10**8), start_ledger=1)
    assert p.min_ratio == Decimal("0.01")
    assert p.model == "haircut"
