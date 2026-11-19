"""Audio side-feature service (NOT part of the Scam Shield scoring). Run from audio/:

    .venv/bin/uvicorn service.main:app --port 8002

Separate process from the main backend on purpose: heavy deps (scipy/matplotlib), long CPU runs,
and it must never affect the competition detector. Uploaded audio is processed in a temp dir and
deleted immediately; nothing is stored or logged.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Path as PathParam, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from . import claim, pipeline

log = logging.getLogger("audio")
logging.basicConfig(level=logging.INFO)

MAX_UPLOAD = 60 * 1024 * 1024  # 60 MB
ALLOWED_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".webm", ".flac", ".mp4", ".mov", ".3gp"}


def _to_wav(src: str, dst: str) -> None:
    """Any audio/video → 8 kHz mono 16-bit WAV with ffmpeg (one decoder for both engines; the browser's
    double resampling made DOPPLERGEIST miss real fly-overs)."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg missing")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "8000",
                    "-c:a", "pcm_s16le", dst], check=True, capture_output=True, timeout=300)
SCENARIO_PATTERN = "^(" + "|".join(pipeline.SCENARIOS) + ")$"

_demo_cache: dict[str, dict] = {}
_demo_locks: dict[str, asyncio.Lock] = {}


async def _demo(scenario: str) -> dict:
    if scenario in _demo_cache:
        return _demo_cache[scenario]
    lock = _demo_locks.setdefault(scenario, asyncio.Lock())
    async with lock:  # one CPU-heavy run per scenario, concurrent callers wait for it
        if scenario not in _demo_cache:
            _demo_cache[scenario] = await run_in_threadpool(pipeline.demo, scenario)
    return _demo_cache[scenario]


async def _warm_all() -> None:
    await _claim(_default_claim())  # ~6 s, so it is ready first
    for sc in pipeline.SCENARIOS:  # one after another: each run is CPU-heavy
        await _demo(sc)


_claim_cache: dict[str, dict] = {}
_claim_lock = asyncio.Lock()


def _default_claim() -> str:
    return claim.claimed_place(" ".join(t for _, t in claim.TRANSCRIPT)) or "madrid"


async def _claim(key: str) -> dict:
    async with _claim_lock:
        if key not in _claim_cache:
            _claim_cache[key] = await run_in_threadpool(claim.verify_claim, key)
    return _claim_cache[key]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm every demo scenario in the background so the live demo answers instantly (~30 s each).
    task = asyncio.create_task(_warm_all())
    yield
    task.cancel()


app = FastAPI(title="Scam Shield — audio side feature", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:4200").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/audio/health")
def health() -> dict:
    return {"status": "ok", "demo_ready": [sc for sc in pipeline.SCENARIOS if sc in _demo_cache],
            "scenarios": {k: {"country": v["country"], "place": v["place"]} for k, v in pipeline.SCENARIOS.items()}}


@app.post("/api/audio/audit")
async def audit(
    file: UploadFile = File(...),
    engine: str = Query("standard", pattern="^(standard|dopplergeist)$"),
) -> dict:
    """Privacy self-check of the user's OWN recording. Any common audio/video format (decoded with ffmpeg).
    engine=standard: vendored afg detector + Doppler physics check · engine=dopplergeist: DOPPLERGEIST discovery."""
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Fișierul este prea mare (maxim 60 MB).")
    if not data:
        raise HTTPException(400, "Fișierul este gol.")
    suffix = Path(file.filename or "").suffix.lower()
    suffix = suffix if suffix in ALLOWED_SUFFIXES else ".bin"
    with tempfile.TemporaryDirectory(prefix="audio_audit_") as work:
        src, wav = os.path.join(work, "in" + suffix), os.path.join(work, "rec.wav")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            await run_in_threadpool(_to_wav, src, wav)
        except Exception as e:
            log.warning("decode failed: %s", type(e).__name__)
            raise HTTPException(422, "Nu am putut citi înregistrarea. Încercați mp3, m4a, wav sau ogg.") from e
        try:
            fn = pipeline.audit_dopplergeist if engine == "dopplergeist" else pipeline.audit
            return await run_in_threadpool(fn, wav)
        except Exception as e:
            log.warning("audit failed: %s", type(e).__name__)
            raise HTTPException(422, "Nu am putut analiza înregistrarea.") from e


@app.get("/api/audio/demo")
async def demo(scenario: str = Query("ro", pattern=SCENARIO_PATTERN)) -> dict:
    """Full localisation on a SYNTHETIC recording placed at a real area (~30 s the first time, then cached)."""
    return await _demo(scenario)


@app.get("/api/audio/demo/{scenario}/recording.wav")
async def demo_recording(scenario: str = PathParam(pattern=SCENARIO_PATTERN)) -> FileResponse:
    """The simulated recording itself (24 min, 4 kHz), so it can be played or downloaded."""
    await _demo(scenario)
    path = pipeline.RECORDINGS_DIR / f"{scenario}.wav"
    if not path.is_file():
        raise HTTPException(404, "Înregistrarea nu este disponibilă.")
    return FileResponse(path, media_type="audio/wav", filename=f"scam-shield-demo-{scenario}.wav")


CLAIM_PATTERN = "^(" + "|".join(claim.PLACES) + ")$"


@app.get("/api/audio/claim")
async def claim_check(claimed: str | None = Query(None, pattern=CLAIM_PATTERN)) -> dict:
    """„Nepotul e în Spania?” — SYNTHETIC voice message from a fake grandson; checks the place he CLAIMS
    (from the transcript, or `claimed`) against the aircraft heard behind him, using the known message time.
    City-level verdict only: never returns the other person's coordinates."""
    return await _claim(claimed or _default_claim())


@app.get("/api/audio/claim/recording.wav")
async def claim_recording() -> FileResponse:
    """The simulated voice message (voice + aircraft in the background), ~100 s."""
    await _claim(_default_claim())
    path = pipeline.RECORDINGS_DIR / "claim.wav"
    if not path.is_file():
        raise HTTPException(404, "Mesajul vocal nu este disponibil.")
    return FileResponse(path, media_type="audio/wav", filename="scam-shield-mesaj-vocal.wav")
