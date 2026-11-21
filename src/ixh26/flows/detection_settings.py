"""Validated API and persistence format for the detector engine's shared thresholds."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, WithJsonSchema

from ixh26.core.detection import DetectionSettings
from ixh26.store.detection_settings import (
    StaleDetectorSettings,
    append_detector_settings,
    latest_detector_settings,
)
from ixh26.store.models import DetectorSettingsRow
from ixh26.store.repo import Store, aware

__all__ = [
    "DetectorSettingsUpdate",
    "DetectorSettingsView",
    "StaleDetectorSettings",
    "effective_detection_settings",
    "read_detector_settings",
    "save_detector_settings",
]

_WINDOW_FIELDS = (
    ("funnel_window", "funnel_window_seconds"),
    ("wash_window", "wash_window_seconds"),
    ("liquidity_window", "liquidity_window_seconds"),
    ("takeover_window", "takeover_window_seconds"),
)
_MAX_INTEGER = 2**31 - 1
_DECIMAL_PATTERN = r"^[0-9]+(?:\.[0-9]+)?$"
_DROPS_PATTERN = r"^[0-9]{1,18}$"


def _parse_decimal(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(_DECIMAL_PATTERN, value):
        raise ValueError("use a plain decimal string of up to 64 characters")
    return Decimal(value)


def _parse_drops(value: object) -> int:
    if not isinstance(value, str) or not re.fullmatch(_DROPS_PATTERN, value):
        raise ValueError("use a string of 1 to 18 digits for whole XRP drops")
    return int(value)


PositiveInt = Annotated[int, Field(strict=True, ge=1, le=_MAX_INTEGER)]
RepeatedCount = Annotated[int, Field(strict=True, ge=2, le=_MAX_INTEGER)]
ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_parse_decimal),
    PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": _DECIMAL_PATTERN, "maxLength": 64}),
]
PositiveFraction = Annotated[
    ExactDecimal, Field(gt=0, le=1, description="Ratio greater than zero and at most one.")
]
Drops = Annotated[
    int,
    BeforeValidator(_parse_drops),
    Field(gt=0),
    PlainSerializer(str, return_type=str, when_used="json"),
    WithJsonSchema(
        {"type": "string", "pattern": _DROPS_PATTERN, "description": "Positive XRP drops."}
    ),
]


class DetectorThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    funnel_window_seconds: PositiveInt
    funnel_min_senders: RepeatedCount
    funnel_min_fraction: PositiveFraction
    wash_window_seconds: PositiveInt
    wash_min_pair_fills: RepeatedCount
    wash_min_fills: RepeatedCount
    wash_max_wallets: RepeatedCount
    wash_max_net_ratio: Annotated[
        ExactDecimal, Field(ge=0, le=1, description="Ratio from zero to one, inclusive.")
    ]
    wash_min_market_share: PositiveFraction
    liquidity_window_seconds: PositiveInt
    liquidity_min_buyers: PositiveInt
    liquidity_min_pool_drops: Drops
    liquidity_min_drop: PositiveFraction
    liquidity_sale_size: Annotated[ExactDecimal, Field(gt=0, description="Positive token amount.")]
    takeover_window_seconds: PositiveInt
    takeover_min_outflow: PositiveFraction

    @classmethod
    def defaults(cls) -> DetectorThresholds:
        values = asdict(DetectionSettings())
        for engine_field, api_field in _WINDOW_FIELDS:
            values[api_field] = int(values.pop(engine_field).total_seconds())
        for name, value in values.items():
            if isinstance(value, Decimal) or name == "liquidity_min_pool_drops":
                values[name] = str(value)
        return cls.model_validate(values)

    def to_engine(self) -> DetectionSettings:
        values = self.model_dump(exclude={api_field for _, api_field in _WINDOW_FIELDS})
        values.update(
            {
                engine_field: timedelta(seconds=getattr(self, api_field))
                for engine_field, api_field in _WINDOW_FIELDS
            }
        )
        return DetectionSettings(**values)


class DetectorSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(strict=True, ge=0)
    thresholds: DetectorThresholds


class DetectorSettingsView(BaseModel):
    version: int
    thresholds: DetectorThresholds
    defaults: DetectorThresholds
    updated_at: datetime | None


def _view(row: DetectorSettingsRow | None) -> DetectorSettingsView:
    defaults = DetectorThresholds.defaults()
    if row is None:
        return DetectorSettingsView(
            version=0, thresholds=defaults, defaults=defaults, updated_at=None
        )
    return DetectorSettingsView(
        version=row.version,
        thresholds=DetectorThresholds.model_validate(row.thresholds),
        defaults=defaults,
        updated_at=aware(row.updated_at),
    )


def read_detector_settings(store: Store) -> DetectorSettingsView:
    return _view(latest_detector_settings(store))


def save_detector_settings(
    store: Store, update: DetectorSettingsUpdate, analyst_id: int
) -> DetectorSettingsView:
    return _view(
        append_detector_settings(
            store,
            expected_version=update.version,
            thresholds=update.thresholds.model_dump(mode="json"),
            analyst_id=analyst_id,
        )
    )


def effective_detection_settings(store: Store) -> DetectionSettings:
    row = latest_detector_settings(store)
    if row is None:
        return DetectionSettings()
    return DetectorThresholds.model_validate(row.thresholds).to_engine()
