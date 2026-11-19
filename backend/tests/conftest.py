import csv
import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import Database
from app.detector.client import DetectorClient
from app.main import create_app

KIT = Path(__file__).resolve().parents[2] / "Scam_Shield_Public_Kit"
SCENARIOS = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((KIT / "validation_set").glob("*.json"))}
EXPECTED = {r["id"]: r for r in csv.DictReader((KIT / "validation_expected_results.csv").open(encoding="utf-8"))}


class AnswerKeyDetector:
    """Fake detector: answers from validation_expected_results.csv (flags put on the first_alert message)."""

    def load(self) -> None: ...

    def analyze(self, scenario: dict) -> dict:
        row = EXPECTED.get(scenario["id"], {"verdict": "SAFE", "scam_type": "NONE", "first_alert": "", "red_flags": ""})
        flags = [f for f in row["red_flags"].split(";") if f]
        fa = int(row["first_alert"]) if row["first_alert"] else None
        return {
            "id": scenario["id"],
            "verdict": row["verdict"],
            "scam_type": row["scam_type"],
            "risk_score": 0,
            "first_alert": fa,
            "red_flags": flags,
            "flags_by_message": [
                {"n": m["n"], "flags": flags if m["n"] == fa else [], "score_after": 0} for m in scenario["messages"]
            ],
            "warning": {"ro": f"Avertisment {scenario['id']}"},
        }


@pytest.fixture
def db() -> Database:
    return Database("sqlite://")


@pytest.fixture
def client(db: Database):
    app = create_app(db=db, detector=DetectorClient(AnswerKeyDetector()))
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cid() -> dict:
    return {"X-Client-Id": str(uuid.uuid4())}
