"""FastAPI entrypoint. Run: uvicorn app.main:app --reload --port 8000 (from backend/)."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analyze, auth, history, report, system
from app.config import get_settings
from app.db import repository as repo
from app.db.models import user_uuid
from app.db.session import Database
from app.detector.client import DetectorClient, DetectorUnavailable
from app.schemas import Scenario
from app.schemas.storage import MAX_RETENTION_HOURS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _seed_admin_validation(db: Database, detector: DetectorClient) -> None:
    """Attribute the default validation JSONs to `admin` on startup if admin has no saved rows yet."""
    folder = get_settings().kit_dir / "validation_set"
    if not db.ready or not folder.is_dir():
        return
    with db.sessionmaker.begin() as s:
        if repo.admin_has_conversations(s):
            return
        admin_id = user_uuid("admin")
        for p in sorted(folder.glob("*.json")):
            sc = Scenario.model_validate(json.loads(p.read_text(encoding="utf-8")))
            res = detector.analyze(sc)
            repo.save_conversation(s, admin_id, sc, res, MAX_RETENTION_HOURS)


def create_app(db: Database | None = None, detector: DetectorClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        # Loaded ONCE per process and kept in memory (run uvicorn with a single worker).
        app.state.detector = detector or DetectorClient()
        app.state.detector.load()
        chosen_db = db or Database(settings.database_url)
        if not chosen_db.init() and db is None:
            # Local SQLite fallback when Postgres isn't running so login & cross-tenant history work out of the box.
            data_dir = Path(settings.storage_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            chosen_db = Database(f"sqlite:///{data_dir / 'scamshield.db'}")
            chosen_db.init()
            log.info("Postgres unavailable; using local SQLite DB at %s", data_dir / "scamshield.db")
        app.state.db = chosen_db
        if db is None:
            _seed_admin_validation(chosen_db, app.state.detector)
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

    for r in (system.router, auth.router, analyze.router, history.router, report.router):
        app.include_router(r, prefix="/api")
    return app


app = create_app()
