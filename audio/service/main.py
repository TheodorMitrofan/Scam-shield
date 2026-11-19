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
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from . import pipeline

log = logging.getLogger("audio")
logging.basicConfig(level=logging.INFO)

MAX_UPLOAD = 60 * 1024 * 1024  # 60 MB of WAV ≈ 1 h at 8 kHz mono 16-bit
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
async def audit(file: UploadFile = File(...)) -> dict:
    """Privacy self-check of the user's OWN recording. Expects WAV (the frontend converts other formats)."""
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Fișierul este prea mare (maxim 60 MB).")
    if not data:
        raise HTTPException(400, "Fișierul este gol.")
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="afg_audit_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        try:
            return await run_in_threadpool(pipeline.audit, path)
        except Exception as e:  # unreadable / not a WAV
            log.warning("audit failed: %s", type(e).__name__)
            raise HTTPException(422, "Nu am putut citi înregistrarea. Încercați alt fișier audio.") from e
    finally:
        os.unlink(path)


@app.get("/api/audio/demo")
async def demo(seed: int = Query(DEFAULT_SEED, ge=1, le=10_000)) -> dict:
    """Full localisation on a SYNTHETIC recording (~40 s the first time per seed, then cached)."""
    return await _demo(seed)
