"""The ONLY place the backend talks to the ML side (CLAUDE.md §3 boundary).

Contract with `scam_detector` (owned by the detector team):
    scam_detector.load() -> None                 # load weights once, at startup
    scam_detector.analyze(scenario: dict) -> dict  # official Scenario JSON -> AnalysisResult JSON

Which implementation is used (first match wins):
    1. DETECTOR_URL set (e.g. http://127.0.0.1:8001) -> the `model_detector` HTTP service (see model_detector/README.md)
    2. `scam_detector` importable                     -> in-process
    3. otherwise                                      -> stub (always SAFE)

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


class HttpDetector:
    """Talks to the `model_detector` service (model kept in memory in that process)."""

    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        import httpx

        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout_s)
        self.model_loaded: bool | None = None

    def load(self) -> None:
        # The service loads the model itself; here we only check that it answers (tolerant: it may start later).
        try:
            h = self._http.get("/health").raise_for_status().json()
            self.model_loaded = bool(h.get("model_loaded"))
            log.info("model_detector at %s: engine=%s", self.base_url, h.get("engine"))
        except Exception as e:  # noqa: BLE001
            log.warning("model_detector at %s not reachable yet: %s", self.base_url, e)

    def analyze(self, scenario: dict) -> dict:
        import httpx

        try:
            r = self._http.post("/analyze", json=scenario)
        except httpx.HTTPError as e:
            raise DetectorUnavailable(f"model_detector unreachable at {self.base_url}: {e}") from e
        if r.status_code >= 400:
            raise DetectorUnavailable(f"model_detector error {r.status_code}: {r.text[:200]}")
        return r.json()


class DetectorUnavailable(RuntimeError):
    """The external detector service is down or returned an error (mapped to HTTP 503 by the API)."""


def _sanitize(raw: dict) -> dict:
    """Accept the raw in-process `scam_detector` output too: per-message `new_flags` are the contract's `flags`,
    and evidence without a character span (model-only flags) is dropped."""
    raw = dict(raw)
    fbm = []
    for m in raw.get("flags_by_message") or []:
        m = dict(m)
        if "new_flags" in m:
            m["flags"] = m["new_flags"]
        fbm.append(m)
    raw["flags_by_message"] = fbm
    if raw.get("evidence") is not None:
        raw["evidence"] = [e for e in raw["evidence"] if e.get("span") and len(e["span"]) == 2]
    return raw


class DetectorClient:
    """Wraps the detector module; kept as a singleton on `app.state` (model stays in memory)."""

    def __init__(self, impl: DetectorPort | None = None, url: str | None = None) -> None:
        if impl is None and url is None:
            from app.config import get_settings

            url = get_settings().detector_url or None
        if impl is None and url:
            impl = HttpDetector(url)
            self.is_stub = False
        elif impl is None:
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
        result = AnalysisResult.model_validate(_sanitize(raw))
        result.id = scenario.id  # the id always comes from the input file
        return result
