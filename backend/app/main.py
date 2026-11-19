"""FastAPI entrypoint. Run: uvicorn app.main:app --reload --port 8000 (from backend/)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analyze, history, system
from app.config import get_settings
from app.db.session import Database
from app.detector.client import DetectorClient, DetectorUnavailable

logging.basicConfig(level=logging.INFO)


def create_app(db: Database | None = None, detector: DetectorClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Loaded ONCE per process and kept in memory (run uvicorn with a single worker).
        app.state.detector = detector or DetectorClient()
        app.state.detector.load()
        app.state.db = db or Database(get_settings().database_url)
        app.state.db.init()  # tolerant: if Postgres is down, analysis still works without saving
        yield
        app.state.db.engine.dispose()

    app = FastAPI(title="Scam Shield API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DetectorUnavailable)
    async def _detector_down(_: Request, exc: DetectorUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Detectorul nu este disponibil momentan."})

    for r in (system.router, analyze.router, history.router):
        app.include_router(r, prefix="/api")
    return app


app = create_app()
