import csv
import json
from pathlib import Path

import pytest

from app.detector.client import DetectorClient
from app.schemas import (
    AnalysisResult,
    AnalyzeTextRequest,
    SaveOptions,
    ScamType,
    Scenario,
    Verdict,
)

KIT = Path(__file__).resolve().parents[2] / "Scam_Shield_Public_Kit"
FILES = sorted((KIT / "validation_set").glob("*.json"))
EXPECTED = list(csv.DictReader((KIT / "validation_expected_results.csv").open(encoding="utf-8")))


def test_kit_present():
    assert len(FILES) == 11 and len(EXPECTED) == 11


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_scenario_roundtrip_is_lossless(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    sc = Scenario.model_validate(raw)
    assert sc.to_detector_input() == raw  # detector receives exactly the official format


@pytest.mark.parametrize("row", EXPECTED, ids=lambda r: r["id"])
def test_official_formula_matches_answer_key(row: dict):
    flags = [f for f in row["red_flags"].split(";") if f]
    res = AnalysisResult.model_validate(
        {
            "id": row["id"],
            "verdict": "SAFE",  # deliberately wrong: the DTO must recompute it
            "scam_type": row["scam_type"],
            "risk_score": 0,
            "first_alert": int(row["first_alert"]) if row["first_alert"] else None,
            "red_flags": flags,
            "warning": {"ro": "x"},
        }
    )
    assert res.risk_score == int(row["risk_score"])
    assert res.verdict == Verdict(row["verdict"])
    assert res.scam_type == ScamType(row["scam_type"])


def test_safe_normalisation():
    res = AnalysisResult.model_validate(
        {"id": "X", "verdict": "SCAM", "scam_type": "MARKETPLACE", "risk_score": 99,
         "first_alert": 2, "red_flags": ["RF_URGENCY"], "warning": {"ro": "x"}}
    )
    assert (res.verdict, res.scam_type, res.first_alert, res.risk_score) == (Verdict.SAFE, ScamType.NONE, None, 15)


def test_robust_inputs():
    for text in ["", "😀😀😀", "a" * 15000, "Cardul dvs a fost blocat, accesati link"]:
        sc = AnalyzeTextRequest(text=text).to_scenario()
        assert sc.id == "PASTE" and sc.messages[0].text == text
    sc = Scenario.model_validate({"id": "T1", "channel": "sms", "messages": [], "extra": 1})
    assert sc.sender.known_contact is False


def test_stub_detector_returns_valid_result():
    client = DetectorClient()
    client.load()
    sc = Scenario.model_validate(json.loads(FILES[3].read_text(encoding="utf-8")))
    res = client.analyze(sc)
    assert res.id == sc.id and len(res.flags_by_message) == len(sc.messages)


def test_save_defaults_to_false():
    assert SaveOptions().save is False
