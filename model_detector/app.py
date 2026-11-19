"""Scam Shield model detector — standalone local HTTP API around the `scam_detector` engine.

Run (from the repo root):
    uvicorn model_detector.app:app --port 8001
    # or: python -m model_detector

The model (rules + fine-tuned BERT ensemble) is loaded ONCE at startup and kept in memory.
Without weights in models/scam-bert it runs rules-only (still 30/30 on the validation set).
Nothing leaves the machine: no cloud calls.

Endpoints (all JSON):
    GET  /health            -> { status, engine, model_loaded, version }
    GET  /info              -> red-flag points, verdict bands, scam types
    POST /analyze           Scenario            -> AnalysisResult
    POST /analyze/batch     Scenario[]          -> AnalysisResult[] (same order as input)
    POST /analyze/text      { text, channel?, sender_name?, sender_address?, known_contact? } -> AnalysisResult
"""
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Use the in-repo detector package even when it is not pip-installed.
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "detector") not in sys.path:
    sys.path.insert(0, str(_REPO / "detector"))

import scam_detector as sd  # noqa: E402
from scam_detector.catalog import get_catalog  # noqa: E402

from .contract import to_contract  # noqa: E402

VERSION = "1.0.0"
MAX_BATCH = 500
_lock = threading.Lock()  # one inference at a time: the torch model is shared and not re-entrant


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    channel: str = "sms"
    sender_name: str | None = None
    sender_address: str | None = None
    known_contact: bool = False
    id: str = "PASTE"


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.time()
    app.state.model_loaded = sd.load(os.environ.get("MODEL_DIR"))
    app.state.load_s = round(time.time() - t0, 2)
    yield


app = FastAPI(title="Scam Shield Model Detector", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("DETECTOR_CORS", "http://localhost:4200,http://localhost:8000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run(scenario: Any) -> dict:
    if not isinstance(scenario, dict):
        raise HTTPException(422, "scenario must be a JSON object")
    with _lock:
        raw = sd.analyze(scenario)
    return to_contract(raw, scenario)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine": "rules+model" if sd.model_loaded() else "rules",
            "model_loaded": sd.model_loaded(), "load_seconds": getattr(app.state, "load_s", None), "version": VERSION}


@app.get("/info")
def info() -> dict:
    cat = get_catalog()
    return {"red_flag_points": cat.points, "verdict_bands": cat.bands, "scam_types": cat.scam_types}


@app.post("/analyze")
def analyze(scenario: dict[str, Any]) -> dict:
    return _run(scenario)


@app.post("/analyze/batch")
def analyze_batch(scenarios: list[dict[str, Any]]) -> list[dict]:
    if len(scenarios) > MAX_BATCH:
        raise HTTPException(413, f"at most {MAX_BATCH} scenarios per batch")
    return [_run(s) for s in scenarios]


@app.post("/analyze/text")
def analyze_text(req: TextRequest) -> dict:
    with _lock:
        raw = sd.analyze_text(req.text, channel=req.channel, sender_name=req.sender_name,
                              sender_address=req.sender_address, known_contact=req.known_contact, sid=req.id)
    return to_contract(raw, None)
