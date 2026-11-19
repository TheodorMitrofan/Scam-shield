"""Scam Shield model detector — standalone local HTTP API around `scam_detector` (inside `detector/`).

Run (from the repo root):
    python3 -m detector.api --port 8001
    # or with Uvicorn (when fastapi + uvicorn are installed):
    uvicorn detector.api.app:app --port 8001

The SOTA v3 model (`scam_detector` + trained_model.joblib) is loaded ONCE at startup and kept in memory.
Nothing leaves the machine: no cloud calls.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

# Ensure `detector/` is on sys.path so `import scam_detector` always works regardless of CWD.
_DETECTOR_DIR = Path(__file__).resolve().parents[1]
if str(_DETECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(_DETECTOR_DIR))

import scam_detector as sd  # noqa: E402
from scam_detector.catalog import get_catalog  # noqa: E402

from .contract import to_contract  # noqa: E402

VERSION = "3.0.0"
MAX_BATCH = 500
MAX_TEXT_LEN = 50_000
_lock = threading.Lock()
_load_s: float | None = None


def _ensure_loaded() -> float:
    global _load_s
    if _load_s is None:
        with _lock:
            if _load_s is None:
                t0 = time.perf_counter()
                sd.load(os.environ.get("MODEL_DIR"))
                _load_s = round(time.perf_counter() - t0, 3)
    return _load_s


def _health_payload() -> dict:
    load_s = _ensure_loaded()
    return {
        "status": "ok",
        "engine": "rules+model" if sd.model_loaded() else "rules",
        "model_loaded": sd.model_loaded(),
        "load_seconds": load_s,
        "version": VERSION,
    }


def _info_payload() -> dict:
    cat = get_catalog()
    return {"red_flag_points": cat.points, "verdict_bands": cat.bands, "scam_types": cat.scam_types}


def _run_scenario(scenario: Any) -> Tuple[int, Any]:
    _ensure_loaded()
    if not isinstance(scenario, dict):
        return 422, {"detail": "scenario must be a JSON object"}
    with _lock:
        raw = sd.analyze(scenario)
    return 200, to_contract(raw, scenario)


def _run_batch(scenarios: Any) -> Tuple[int, Any]:
    _ensure_loaded()
    if not isinstance(scenarios, list):
        return 422, {"detail": "scenarios must be a JSON array"}
    if len(scenarios) > MAX_BATCH:
        return 413, {"detail": f"at most {MAX_BATCH} scenarios per batch"}
    out = []
    for s in scenarios:
        st, body = _run_scenario(s)
        if st != 200:
            return st, body
        out.append(body)
    return 200, out


def _run_text(payload: Any) -> Tuple[int, Any]:
    _ensure_loaded()
    if not isinstance(payload, dict):
        return 422, {"detail": "body must be a JSON object"}
    text = payload.get("text")
    if not isinstance(text, str) or len(text) < 1 or len(text) > MAX_TEXT_LEN or not text.strip():
        return 422, {"detail": f"'text' must be a non-empty string (<= {MAX_TEXT_LEN} chars)"}
    channel = str(payload.get("channel") or "sms")
    sender_name = payload.get("sender_name")
    sender_address = payload.get("sender_address")
    known_contact = bool(payload.get("known_contact", False))
    sid = str(payload.get("id") or "PASTE")
    with _lock:
        raw = sd.analyze_text(
            text,
            channel=channel,
            sender_name=sender_name,
            sender_address=sender_address,
            known_contact=known_contact,
            sid=sid,
        )
    return 200, to_contract(raw, None)


# ---- Optional FastAPI ASGI app (for Uvicorn in Python 3.10+ / backend venv)
app = None
try:
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    class TextRequest(BaseModel):
        text: str = Field(min_length=1, max_length=MAX_TEXT_LEN)
        channel: str = "sms"
        sender_name: str | None = None
        sender_address: str | None = None
        known_contact: bool = False
        id: str = "PASTE"

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _ensure_loaded()
        yield

    app = FastAPI(title="Scam Shield Model Detector", version=VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in os.environ.get("DETECTOR_CORS", "http://localhost:4200,http://localhost:8000").split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return _health_payload()

    @app.get("/info")
    def info() -> dict:
        return _info_payload()

    @app.post("/analyze")
    def analyze(scenario: dict[str, Any]) -> dict:
        st, body = _run_scenario(scenario)
        if st >= 400:
            raise HTTPException(st, body.get("detail", "error"))
        return body

    @app.post("/analyze/batch")
    def analyze_batch(scenarios: list[dict[str, Any]]) -> list[dict]:
        st, body = _run_batch(scenarios)
        if st >= 400:
            raise HTTPException(st, body.get("detail", "error"))
        return body

    @app.post("/analyze/text")
    def analyze_text(req: TextRequest) -> dict:
        st, body = _run_text(req.model_dump())
        if st >= 400:
            raise HTTPException(st, body.get("detail", "error"))
        return body
except ImportError:
    pass


# ---- Flask & stdlib HTTP fallback (works cleanly out of the box without FastAPI)
def create_flask_app():
    from flask import Flask, Response, request

    _ensure_loaded()
    fapp = Flask("detector.api")

    @fapp.after_request
    def _cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = os.environ.get("DETECTOR_CORS", "*")
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    def _resp(status: int, data: Any) -> Response:
        return Response(json.dumps(data, ensure_ascii=False), status=status, mimetype="application/json")

    @fapp.route("/health", methods=["GET"])
    def f_health():
        return _resp(200, _health_payload())

    @fapp.route("/info", methods=["GET"])
    def f_info():
        return _resp(200, _info_payload())

    @fapp.route("/analyze", methods=["POST"])
    def f_analyze():
        data = request.get_json(silent=True)
        if data is None:
            return _resp(422, {"detail": "Invalid JSON body"})
        return _resp(*_run_scenario(data))

    @fapp.route("/analyze/batch", methods=["POST"])
    def f_batch():
        data = request.get_json(silent=True)
        if data is None:
            return _resp(422, {"detail": "Invalid JSON body"})
        return _resp(*_run_batch(data))

    @fapp.route("/analyze/text", methods=["POST"])
    def f_text():
        data = request.get_json(silent=True)
        if data is None:
            return _resp(422, {"detail": "Invalid JSON body"})
        return _resp(*_run_text(data))

    return fapp


def run_fallback_server(host: str = "127.0.0.1", port: int = 8001) -> None:
    _ensure_loaded()
    try:
        fapp = create_flask_app()
        print(f"detector.api (Flask) listening on http://{host}:{port} | model_loaded={sd.model_loaded()}")
        fapp.run(host=host, port=port, threaded=True, use_reloader=False)
        return
    except ImportError:
        pass

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send(self, st: int, data: Any):
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(st)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, _health_payload())
            elif self.path == "/info":
                self._send(200, _info_payload())
            else:
                self._send(404, {"detail": "Not found"})

        def do_POST(self):
            ln = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(ln) if ln > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send(422, {"detail": "Invalid JSON body"})
                return
            if self.path == "/analyze":
                self._send(*_run_scenario(data))
            elif self.path == "/analyze/batch":
                self._send(*_run_batch(data))
            elif self.path == "/analyze/text":
                self._send(*_run_text(data))
            else:
                self._send(404, {"detail": "Not found"})

    print(f"detector.api (stdlib) listening on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
