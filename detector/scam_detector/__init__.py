from __future__ import annotations

import os
from typing import Dict, Optional

from .catalog import Catalog, FLAG_ORDER, get_catalog
from .pipeline import ScamShieldPipeline
from .sequential_engine import SequentialEngine
from .warning_generator import WarningGenerator

_PIPELINE: Optional[ScamShieldPipeline] = None
_MODEL = None
_LOAD_ATTEMPTED = False


def load(model_dir: Optional[str] = None) -> bool:
    """Load catalog, rules, semantic NLI index, and trained SOTA v3 ensemble once."""
    global _PIPELINE, _MODEL, _LOAD_ATTEMPTED
    _LOAD_ATTEMPTED = True
    _PIPELINE = ScamShieldPipeline()
    if os.environ.get("SCAM_RULES_ONLY") == "1":
        _MODEL = None
        _PIPELINE.engine.scam_classifier.model = None
        _PIPELINE.engine.scam_classifier._type_pipeline = None
        _PIPELINE.engine.red_flag_detector.semantic_nli._ml_flag_pipeline = None
        _PIPELINE.engine.red_flag_detector.semantic_nli._ml_risk_pipeline = None
        return False
    _MODEL = _PIPELINE.engine.scam_classifier.model
    return _MODEL is not None


def model_loaded() -> bool:
    return _MODEL is not None


def analyze(scenario: Dict) -> Dict:
    if not _LOAD_ATTEMPTED or _PIPELINE is None:
        load()
    if not isinstance(scenario, dict):
        scenario = {}
    raw = _PIPELINE.analyze_scenario(scenario)
    out = _PIPELINE.to_backend_contract(raw)
    out["engine"] = "rules+model" if _MODEL is not None else "rules"
    return out


def analyze_text(
    text: str,
    channel: str = "sms",
    sender_name: Optional[str] = None,
    sender_address: Optional[str] = None,
    known_contact: bool = False,
    sid: str = "CUSTOM",
) -> Dict:
    return analyze({
        "id": sid,
        "channel": channel,
        "sender": {
            "name": sender_name,
            "address": sender_address,
            "known_contact": known_contact,
        },
        "messages": [{"n": 1, "from": "sender", "text": text}],
    })


__all__ = [
    "Catalog",
    "FLAG_ORDER",
    "get_catalog",
    "ScamShieldPipeline",
    "SequentialEngine",
    "WarningGenerator",
    "load",
    "model_loaded",
    "analyze",
    "analyze_text",
]
