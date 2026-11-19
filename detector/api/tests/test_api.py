"""Tests for detector/api HTTP service (supports FastAPI TestClient or Flask test client)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "Scam_Shield_Public_Kit"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detector.api.app import app as fastapi_app, create_flask_app  # noqa: E402

SCENARIOS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((KIT / "validation_set").glob("*.json"))]
EXPECTED = {r["id"]: r for r in csv.DictReader((KIT / "validation_expected_results.csv").open(encoding="utf-8-sig"))}
WINDOWS = {"V11": (3, 5)}


def _make_client():
    if fastapi_app is not None:
        from fastapi.testclient import TestClient
        return TestClient(fastapi_app), True
    return create_flask_app().test_client(), False


def _json(resp, is_fastapi: bool):
    return resp.json() if is_fastapi else resp.get_json()


def run_all_tests():
    c, is_fa = _make_client()
    if is_fa:
        c.__enter__()
    try:
        h = _json(c.get("/health"), is_fa)
        assert h["status"] == "ok" and h["engine"] == "rules+model" and h["model_loaded"] is True

        info = _json(c.get("/info"), is_fa)
        assert info["red_flag_points"]["RF_CODE_REQUEST"] == 35 and "SCAM" in info["verdict_bands"]

        for s in SCENARIOS:
            r = _json(c.post("/analyze", json=s), is_fa)
            e = EXPECTED[s["id"]]
            assert (r["verdict"], r["scam_type"]) == (e["verdict"], e["scam_type"]), s["id"]
            if e["first_alert"]:
                lo, hi = WINDOWS.get(s["id"], (int(e["first_alert"]),) * 2)
                assert lo <= r["first_alert"] <= hi, s["id"]

        r4 = _json(c.post("/analyze", json=SCENARIOS[3]), is_fa)
        assert set(r4) >= {"id", "verdict", "scam_type", "risk_score", "first_alert", "red_flags", "flags_by_message", "warning", "evidence"}
        seen = []
        for m in r4["flags_by_message"]:
            assert not set(m["flags"]) & set(seen)
            seen += m["flags"]
        assert set(seen) == set(r4["red_flags"])
        assert all(isinstance(e["span"], list) and len(e["span"]) == 2 for e in r4["evidence"])

        rs = _json(c.post("/analyze/batch", json=SCENARIOS), is_fa)
        assert [r["id"] for r in rs] == [s["id"] for s in SCENARIOS]

        rt = _json(c.post("/analyze/text", json={"text": "Banca: contul dvs a fost blocat. Trimiteti-ne codul primit prin SMS."}), is_fa)
        assert rt["verdict"] == "SCAM" and rt["id"] == "PASTE"

        for body in [{}, {"messages": None}, {"messages": [None, 5, {"text": None}]}, {"id": 3, "messages": "x"}]:
            assert c.post("/analyze", json=body).status_code == 200

        assert c.post("/analyze", json=[1, 2]).status_code == 422
        print("ALL detector/api end-to-end tests PASSED 100%!")
    finally:
        if is_fa:
            c.__exit__(None, None, None)


def test_api_end_to_end():
    run_all_tests()


if __name__ == "__main__":
    run_all_tests()
