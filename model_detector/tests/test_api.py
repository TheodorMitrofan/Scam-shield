"""pytest model_detector/tests  (from the repo root; SCAM_RULES_ONLY=1 to skip the model)"""
import csv
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "Scam_Shield_Public_Kit"
sys.path.insert(0, str(ROOT))

from model_detector.app import app  # noqa: E402

SCENARIOS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((KIT / "validation_set").glob("*.json"))]
EXPECTED = {r["id"]: r for r in csv.DictReader((KIT / "validation_expected_results.csv").open(encoding="utf-8-sig"))}
WINDOWS = {"V11": (3, 5)}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["engine"] in ("rules", "rules+model")


def test_info(client):
    i = client.get("/info").json()
    assert i["red_flag_points"]["RF_CODE_REQUEST"] == 35 and "SCAM" in i["verdict_bands"]


def test_validation_set_matches_answer_key(client):
    for s in SCENARIOS:
        r = client.post("/analyze", json=s).json()
        e = EXPECTED[s["id"]]
        assert (r["verdict"], r["scam_type"]) == (e["verdict"], e["scam_type"]), s["id"]
        if e["first_alert"]:
            lo, hi = WINDOWS.get(s["id"], (int(e["first_alert"]),) * 2)
            assert lo <= r["first_alert"] <= hi, s["id"]


def test_contract_shape(client):
    r = client.post("/analyze", json=SCENARIOS[3]).json()
    assert set(r) >= {"id", "verdict", "scam_type", "risk_score", "first_alert", "red_flags", "flags_by_message",
                      "warning", "evidence"}
    seen = []
    for m in r["flags_by_message"]:
        assert not set(m["flags"]) & set(seen), "flags must be the ones FIRST detected in message n"
        seen += m["flags"]
    assert set(seen) == set(r["red_flags"])
    assert all(isinstance(e["span"], list) and len(e["span"]) == 2 for e in r["evidence"])


def test_batch_keeps_order(client):
    rs = client.post("/analyze/batch", json=SCENARIOS).json()
    assert [r["id"] for r in rs] == [s["id"] for s in SCENARIOS]


def test_text(client):
    r = client.post("/analyze/text", json={"text": "Banca: contul dvs a fost blocat. Trimiteti-ne codul primit prin SMS."}).json()
    assert r["verdict"] == "SCAM" and r["id"] == "PASTE"


@pytest.mark.parametrize("body", [{}, {"messages": None}, {"messages": [None, 5, {"text": None}]}, {"id": 3, "messages": "x"}])
def test_malformed_does_not_crash(client, body):
    assert client.post("/analyze", json=body).status_code == 200


def test_not_an_object(client):
    assert client.post("/analyze", json=[1, 2]).status_code == 422


def test_backend_client_end_to_end(client):
    """The backend's DetectorClient, over HTTP, validates every response with its own DTOs."""
    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from app.detector.client import DetectorClient, HttpDetector
        from app.schemas import Scenario
    except ImportError as e:  # backend deps (pydantic-settings, sqlalchemy) not installed here
        pytest.skip(f"backend not importable: {e}")
    http = HttpDetector("http://model-detector")
    http._http = client  # TestClient is an httpx.Client
    dc = DetectorClient(http)
    dc.load()
    for s in SCENARIOS:
        res = dc.analyze(Scenario.model_validate(s))
        assert res.verdict.value == EXPECTED[s["id"]]["verdict"], s["id"]
