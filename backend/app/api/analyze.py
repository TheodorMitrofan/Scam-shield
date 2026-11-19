"""Analyze controllers. Every endpoint takes the consent flag `?save=` (default false)."""

from fastapi import APIRouter, Body
from fastapi.concurrency import run_in_threadpool

from app.schemas import AnalyzeResponse, AnalyzeTextRequest, Scenario
from app.services.analysis import analyze_and_maybe_save

from .deps import Db, Detector, Save

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalyzeResponse)
async def analyze(scenario: Scenario, detector: Detector, db: Db, opts: Save) -> AnalyzeResponse:
    """Analyse one scenario JSON. `?save=true` (+ `X-Client-Id`) stores it; otherwise nothing is stored."""
    return (await run_in_threadpool(analyze_and_maybe_save, detector, db, [scenario], opts))[0]


@router.post("/batch", response_model=list[AnalyzeResponse])
async def analyze_batch(
    detector: Detector, db: Db, opts: Save, scenarios: list[Scenario] = Body(max_length=500)
) -> list[AnalyzeResponse]:
    """Dashboard: a whole folder at once, sorted by scenario id."""
    ordered = sorted(scenarios, key=lambda s: s.id)
    return await run_in_threadpool(analyze_and_maybe_save, detector, db, ordered, opts)


@router.post("/text", response_model=AnalyzeResponse)
async def analyze_text(body: AnalyzeTextRequest, detector: Detector, db: Db, opts: Save) -> AnalyzeResponse:
    """Pasted message → 1-message scenario with id "PASTE"."""
    return (await run_in_threadpool(analyze_and_maybe_save, detector, db, [body.to_scenario()], opts))[0]
