"""Audio side-feature service (NOT part of the Scam Shield scoring). Run from audio/:

    .venv/bin/uvicorn service.main:app --port 8001

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

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from . import pipeline

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
DEFAULT_SEED = 23

_demo_cache: dict[int, dict] = {}
_demo_locks: dict[int, asyncio.Lock] = {}


async def _demo(seed: int) -> dict:
    if seed in _demo_cache:
        return _demo_cache[seed]
    lock = _demo_locks.setdefault(seed, asyncio.Lock())
    async with lock:  # one CPU-heavy run per seed, concurrent callers wait for it
        if seed not in _demo_cache:
            _demo_cache[seed] = await run_in_threadpool(pipeline.demo, seed)
    return _demo_cache[seed]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the default demo in the background so the live demo answers instantly.
    task = asyncio.create_task(_demo(DEFAULT_SEED))
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
    return {"status": "ok", "demo_ready": DEFAULT_SEED in _demo_cache}


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
async def demo(seed: int = Query(DEFAULT_SEED, ge=1, le=10_000)) -> dict:
    """Full localisation on a SYNTHETIC recording (~40 s the first time per seed, then cached)."""
    return await _demo(seed)
