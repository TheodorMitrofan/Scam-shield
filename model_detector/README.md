# model_detector — the detector as a local HTTP API

A small FastAPI service around the `scam_detector` engine (`detector/`, rules + fine-tuned BERT ensemble).
The model is loaded **once** at startup and stays in memory. Everything runs locally; no cloud calls.
Without weights in `models/scam-bert` it runs **rules-only** (still 11/11 on the validation set).

## Run

```bash
# from the repo root
pip install -r model_detector/requirements.txt      # + torch/transformers for the model (optional)
python -m model_detector --port 8001                 # → http://127.0.0.1:8001/docs
```

Env: `MODEL_DIR` (default `models/scam-bert`), `SCAM_RULES_ONLY=1` (skip the model),
`DETECTOR_CORS` (default `http://localhost:4200,http://localhost:8000`).

## Connect the app on `main`

The backend already has the integration point (`backend/app/detector/client.py`). Set one env var:

```bash
# .env (repo root) or the shell that starts the backend
DETECTOR_URL=http://127.0.0.1:8001
```

Then start the backend as usual (`cd backend && uvicorn app.main:app --port 8000`). The frontend doesn't change:
it keeps calling the backend (`/api/analyze`, `/api/analyze/batch`, `/api/analyze/text`). If the detector is
down, the backend answers **503** "Detectorul nu este disponibil momentan." When `DETECTOR_URL` is empty the
backend falls back to in-process `scam_detector` (if installed), then to the always-SAFE stub.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | – | `{ status, engine: "rules"\|"rules+model", model_loaded, load_seconds, version }` |
| GET | `/info` | – | `{ red_flag_points, verdict_bands, scam_types }` |
| POST | `/analyze` | `Scenario` | `AnalysisResult` |
| POST | `/analyze/batch` | `Scenario[]` (≤500) | `AnalysisResult[]`, same order as input |
| POST | `/analyze/text` | `{ text, channel?, sender_name?, sender_address?, known_contact?, id? }` | `AnalysisResult` (blank lines split messages; `Eu:`/`Reader:` = reader) |

`AnalysisResult` is exactly the CLAUDE.md §4.2 contract that `backend/app/schemas/analysis.py` validates:
`flags_by_message[].flags` = flags **first** detected in message n (full set in `all_flags`); `evidence[]` =
`{ n, flag, span: [start, end), source }` character offsets for highlighting. Extra fields: `engine`, `model_type`.

```bash
curl -s -X POST http://127.0.0.1:8001/analyze -H "Content-Type: application/json" \
     --data-binary @Scam_Shield_Public_Kit/validation_set/V04.json
```

Malformed input never crashes the service (empty / null messages → SAFE). One inference runs at a time
(the torch model is shared), so run a single worker.

## Tests

```bash
python -m pytest -q model_detector/tests     # incl. end-to-end through the backend's DetectorClient + DTOs
```
