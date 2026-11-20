from decimal import Decimal

import pytest

from ixh26 import config
from ixh26.ledger.ops import ephemeral_wallet, pay_xrp


@pytest.mark.parametrize("drops", [Decimal(0), Decimal("1.5"), Decimal(-3)])
async def test_payments_need_positive_integer_drops(drops: Decimal) -> None:
    wallet = ephemeral_wallet()
    with pytest.raises(ValueError):
        await pay_xrp(config.load_settings({}), wallet, wallet.classic_address, "rX", drops, "t")


def test_ephemeral_wallets_are_distinct() -> None:
    assert ephemeral_wallet().classic_address != ephemeral_wallet().classic_address
