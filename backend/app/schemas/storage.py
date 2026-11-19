"""DTOs for the consent-based storage (applications → contacts → conversations → messages).

Nothing is stored unless the user ticked the consent checkbox (`save=true` on analyze endpoints).
No accounts: the browser keeps a random `client_id` UUID and sends it as `X-Client-Id`; every read and
delete is scoped to it.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .analysis import AnalysisResult, ScamType, Verdict
from .scenario import Channel, Scenario

DEFAULT_RETENTION_HOURS = 24
MAX_RETENTION_HOURS = 24 * 30


class SaveOptions(BaseModel):
    """Built by the controllers from `?save=&retention_hours=` + `X-Client-Id`."""

    save: bool = False
    client_id: UUID | None = None
    retention_hours: int = Field(default=DEFAULT_RETENTION_HOURS, ge=1, le=MAX_RETENTION_HOURS)


class ApplicationSummary(BaseModel):
    code: Channel
    display_name: str
    view_kind: str
    contacts: int
    conversations: int
    scams: int


class ContactSummary(BaseModel):
    id: UUID
    application: Channel
    address: str
    display_name: str | None
    known_contact: bool
    conversations: int
    last_verdict: Verdict | None
    last_risk_score: int | None
    last_updated: datetime | None


class ConversationSummary(BaseModel):
    """Listing row — verdict only, no message text."""

    id: UUID
    application: Channel
    contact_id: UUID
    external_id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    verdict: Verdict
    scam_type: ScamType
    risk_score: int
    first_alert: int | None
    message_count: int
    owner_username: str | None = None
    owner_role: str | None = None


class ConversationDetail(ConversationSummary):
    """Full conversation: the original scenario, the analysis, and app-specific (EAV) attributes."""

    scenario: Scenario
    result: AnalysisResult
    attributes: dict[str, Any] = Field(default_factory=dict)


class DeleteResponse(BaseModel):
    deleted: int
