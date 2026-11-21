"""Read or append a shared detector settings revision."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ixh26.store.models import DetectorSettingsRow
from ixh26.store.repo import Store


class StaleDetectorSettings(RuntimeError):
    """Another analyst has already saved a more recent revision."""


def latest_detector_settings(store: Store) -> DetectorSettingsRow | None:
    with store.session() as session:
        return session.scalar(
            select(DetectorSettingsRow).order_by(DetectorSettingsRow.version.desc()).limit(1)
        )


def append_detector_settings(
    store: Store, *, expected_version: int, thresholds: dict[str, int | str], analyst_id: int
) -> DetectorSettingsRow:
    try:
        with store.session() as session:
            version = session.scalar(select(func.max(DetectorSettingsRow.version))) or 0
            if version != expected_version:
                raise StaleDetectorSettings
            row = DetectorSettingsRow(
                version=version + 1, thresholds=thresholds, analyst_id=analyst_id
            )
            session.add(row)
            session.flush()
    except IntegrityError as exc:
        # Concurrent writers may both read the same version. Only one can insert its successor.
        latest = latest_detector_settings(store)
        if latest is not None and latest.version != expected_version:
            raise StaleDetectorSettings from exc
        raise
    return row
