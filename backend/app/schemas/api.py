"""Request/response DTOs for the HTTP API (CLAUDE.md §4.1) that are not plain Scenario/AnalysisResult."""

from uuid import UUID

from pydantic import BaseModel, Field

from .analysis import AnalysisResult
from .scenario import Channel, Scenario


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    detector_stub: bool
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
    """Same shape whether or not the user consented to saving (the UI checkbox → `?save=true`)."""

    result: AnalysisResult
    saved: bool = False
    conversation_id: UUID | None = Field(default=None, description="set only when saved")
    client_id: UUID | None = Field(
        default=None, description="set when saved; the browser must keep it and send it as X-Client-Id"
    )


class AudioAnalyzeResponse(AnalyzeResponse):
    """Stage 4: POST /audio → transcript as a call_transcript scenario + its analysis."""

    scenario: Scenario
