"""Analyst-only API for the shared detector configuration."""

from fastapi import APIRouter, HTTPException

from ixh26.app.auth import AnalystDep, StoreDep
from ixh26.flows.detection_settings import (
    DetectorSettingsUpdate,
    DetectorSettingsView,
    StaleDetectorSettings,
    read_detector_settings,
    save_detector_settings,
)

router = APIRouter(prefix="/detection-settings")


@router.get("")
def get_detection_settings(user: AnalystDep, store: StoreDep) -> DetectorSettingsView:
    return read_detector_settings(store)


@router.put("")
def update_detection_settings(
    body: DetectorSettingsUpdate, user: AnalystDep, store: StoreDep
) -> DetectorSettingsView:
    try:
        return save_detector_settings(store, body, user.id)
    except StaleDetectorSettings as exc:
        raise HTTPException(409, "detector settings changed; reload before saving") from exc
