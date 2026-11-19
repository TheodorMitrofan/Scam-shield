"""The ONLY place the backend talks to the ML side (CLAUDE.md §3 boundary).

Contract with `scam_detector` (owned by the detector team):
    scam_detector.load() -> None                 # load weights once, at startup
    scam_detector.analyze(scenario: dict) -> dict  # official Scenario JSON -> AnalysisResult JSON

Everything going in is a validated `Scenario` DTO; everything coming out is validated into an
`AnalysisResult` DTO (which also re-applies the official score/verdict formula).
"""

import logging
from typing import Protocol

from app.schemas import AnalysisResult, Scenario

log = logging.getLogger(__name__)


class DetectorPort(Protocol):
    def load(self) -> None: ...
    def analyze(self, scenario: dict) -> dict: ...


class _StubDetector:
    """HACK: used until the `scam_detector` package is installed — always answers SAFE."""

    def load(self) -> None:
        log.warning("scam_detector not installed: using stub detector (always SAFE)")

    def analyze(self, scenario: dict) -> dict:
        return {
            "id": scenario["id"],
            "verdict": "SAFE",
            "scam_type": "NONE",
            "risk_score": 0,
            "first_alert": None,
            "red_flags": [],
            "flags_by_message": [{"n": m["n"], "flags": [], "score_after": 0} for m in scenario["messages"]],
            "warning": {"ro": "Detectorul nu este încă disponibil.", "en": "Detector not available yet."},
        }


class DetectorClient:
    """Wraps the detector module; kept as a singleton on `app.state` (model stays in memory)."""

    def __init__(self, impl: DetectorPort | None = None) -> None:
        if impl is None:
            try:
                import scam_detector  # type: ignore[import-not-found]

                impl = scam_detector
                self.is_stub = False
            except ImportError:
                impl = _StubDetector()
                self.is_stub = True
        else:
            self.is_stub = False
        self._impl = impl
        self.loaded = False

    def load(self) -> None:
        self._impl.load()
        self.loaded = True

    def analyze(self, scenario: Scenario) -> AnalysisResult:
        raw = self._impl.analyze(scenario.to_detector_input())
        result = AnalysisResult.model_validate(raw)
        result.id = scenario.id  # the id always comes from the input file
        return result
