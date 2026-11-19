# `detector/api` — Local HTTP Service for Scam Shield

Standalone local HTTP API wrapping `scam_detector` on port `8001`.

## Run from repo root
```bash
python3 -m detector.api --port 8001
```
Supports FastAPI/Uvicorn when installed, with automatic Flask / stdlib fallback.

## Test
```bash
python3 detector/api/tests/test_api.py
```
