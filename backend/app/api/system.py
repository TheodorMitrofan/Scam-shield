import json

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.schemas import HealthResponse, Scenario

from .deps import CurrentUser, Db, Detector

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(detector: Detector, db: Db) -> HealthResponse:
    return HealthResponse(model_loaded=detector.loaded, detector_stub=detector.is_stub, db_connected=db.ping())


@router.get("/scenarios/validation", response_model=list[Scenario])
def validation_set(request: Request, user: CurrentUser) -> list[Scenario]:
    if user is not None and user.role != "admin":
        raise HTTPException(403, "Setul implicit de validare aparține administratorului.")
    folder = get_settings().kit_dir / "validation_set"
    if not folder.is_dir():
        raise HTTPException(404, f"Validation set not found at {folder}")
    items = [Scenario.model_validate(json.loads(p.read_text(encoding="utf-8"))) for p in folder.glob("*.json")]
    return sorted(items, key=lambda s: s.id)
