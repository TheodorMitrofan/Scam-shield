"""DTOs for the opt-in history (data saved only with the user's consent).

Privacy rules (brief, non-functional): nothing is stored unless `consent=True`, every record has an
expiry, and the user can delete their own records. There are no accounts: the browser generates a
random `client_id` (UUID kept in localStorage) and sends it as the `X-Client-Id` header, so a user
can list/delete only what they saved.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .analysis import AnalysisResult, ScamType, Verdict
from .scenario import Channel, Scenario

DEFAULT_RETENTION_HOURS = 24
MAX_RETENTION_HOURS = 24 * 30


class SaveConsent(BaseModel):
    """Sent with an analyze request. Default = do not store anything."""

    consent: bool = False
    client_id: UUID | None = Field(default=None, description="required when consent is true")
    retention_hours: int = Field(default=DEFAULT_RETENTION_HOURS, ge=1, le=MAX_RETENTION_HOURS)

    @property
    def should_save(self) -> bool:
        return self.consent and self.client_id is not None


class HistoryCreate(BaseModel):
    """Internal: what the service layer hands to the repository to persist."""

    client_id: UUID
    scenario: Scenario
    result: AnalysisResult
    retention_hours: int = DEFAULT_RETENTION_HOURS
    audio_id: UUID | None = None


class HistoryItemSummary(BaseModel):
    """One row in GET /history — no message content, safe to list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    expires_at: datetime
    scenario_id: str
    channel: Channel
    verdict: Verdict
    scam_type: ScamType
    risk_score: int
    first_alert: int | None


class HistoryItemDetail(HistoryItemSummary):
    """GET /history/{id} — includes the saved conversation and full result."""

    scenario: Scenario
    result: AnalysisResult
    audio_id: UUID | None = None


class HistoryList(BaseModel):
    items: list[HistoryItemSummary]
    total: int


class DeleteResponse(BaseModel):
    deleted: int
