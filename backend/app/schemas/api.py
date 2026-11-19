"""Request/response DTOs for the HTTP API (CLAUDE.md §4.1) that are not plain Scenario/AnalysisResult."""

from pydantic import BaseModel, Field

from .analysis import AnalysisResult
from .scenario import Channel, Scenario


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    db_connected: bool


class AnalyzeTextRequest(BaseModel):
    """Body of POST /analyze/text — pasted free text, wrapped as a 1-message scenario with id "PASTE"."""

    text: str = Field(max_length=20_000)
    channel: Channel = Channel.SMS

    def to_scenario(self) -> Scenario:
        return Scenario.model_validate(
            {
                "id": "PASTE",
                "channel": self.channel,
                "sender": {"name": None, "address": None, "known_contact": False},
                "messages": [{"n": 1, "from": "sender", "text": self.text}],
            }
        )


class AnalyzeResponse(BaseModel):
    """Returned when the caller asked to save (consent): the result plus where it was stored."""

    result: AnalysisResult
    history_id: str | None = Field(default=None, description="set only if the user consented to saving")


class AudioAnalyzeResponse(BaseModel):
    """Stage 4: POST /audio → transcript as a call_transcript scenario + its analysis."""

    scenario: Scenario
    result: AnalysisResult
    history_id: str | None = None
