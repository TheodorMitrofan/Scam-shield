"""DTOs for the fraud report (CLAUDE.md §4.1–4.2).

Flow: POST /report/draft → FraudReportDraft (incident generated, personal data empty)
      → user fills PersonalData in the UI → POST /report/send → e-mail to the demo recipient.
Personal data is never stored or logged; it only goes into the e-mail.
"""

import re
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .analysis import AnalysisResult, RedFlag, ScamType, Verdict
from .scenario import Channel, Scenario

IndicatorKind = Literal["url", "email", "phone", "iban", "amount"]


class ReportDraftRequest(BaseModel):
    scenario: Scenario
    result: AnalysisResult | None = Field(default=None, description="if missing, the detector runs again")


class Indicator(BaseModel):
    kind: IndicatorKind
    value: str = Field(description="exact value, for investigators")
    display: str = Field(description="defanged, non-clickable form for the UI / e-mail")
    message_n: int | None = Field(default=None, description="message where it appears; null = sender field")


class TimelineEntry(BaseModel):
    n: int
    author: Literal["sender", "reader"]
    author_label: str
    text: str
    is_first_alert: bool = False
    flags: list[RedFlag] = Field(default_factory=list)


class FlagExplanation(BaseModel):
    code: RedFlag
    label: str


class SuspectSender(BaseModel):
    name: str | None
    address: str | None
    known_contact: bool


class Incident(BaseModel):
    """The generated part of the report: what happened (read-only in the UI)."""

    scenario_id: str
    channel: Channel
    channel_label: str
    sender: SuspectSender
    verdict: Verdict
    scam_type: ScamType
    scam_type_label: str
    risk_score: int = Field(ge=0, le=100)
    first_alert: int | None
    red_flags: list[FlagExplanation]
    summary_ro: str
    timeline: list[TimelineEntry]
    indicators: list[Indicator]


class PersonalField(BaseModel):
    """Describes one input of the personal-data form, so the UI can render it without guessing."""

    key: str
    label: str
    type: Literal["text", "email", "tel", "date", "time", "number", "checkbox", "textarea"]
    required: bool = False
    hint: str | None = None


_CNP = re.compile(r"^\d{13}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PersonalData(BaseModel):
    """Filled in by the user. All optional in the draft; `validate_for_sending` enforces the minimum."""

    last_name: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    cnp: str | None = Field(default=None, max_length=13)
    id_series_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=200)
    incident_date: date | None = None
    incident_time: time | None = None
    lost_money: bool = False
    amount_lost: float | None = Field(default=None, ge=0)
    bank: str | None = Field(default=None, max_length=100)
    additional_details: str | None = Field(default=None, max_length=5000)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("cnp")
    @classmethod
    def _cnp_format(cls, v: str | None) -> str | None:
        if v is not None and not _CNP.match(v.strip()):
            raise ValueError("CNP-ul trebuie să aibă 13 cifre.")
        return v.strip() if v else v

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str | None) -> str | None:
        if v is not None and not _EMAIL.match(v.strip()):
            raise ValueError("Adresa de e-mail nu pare corectă.")
        return v.strip() if v else v


PERSONAL_FIELDS: list[PersonalField] = [
    PersonalField(key="last_name", label="Nume", type="text", required=True),
    PersonalField(key="first_name", label="Prenume", type="text", required=True),
    PersonalField(key="phone", label="Telefon", type="tel", hint="Telefon sau e-mail: măcar unul"),
    PersonalField(key="email", label="E-mail", type="email", hint="Telefon sau e-mail: măcar unul"),
    PersonalField(key="cnp", label="CNP", type="text", hint="13 cifre (opțional)"),
    PersonalField(key="id_series_number", label="Seria și numărul actului de identitate", type="text"),
    PersonalField(key="address", label="Adresa de domiciliu", type="text"),
    PersonalField(key="incident_date", label="Data la care ați primit mesajul", type="date"),
    PersonalField(key="incident_time", label="Ora aproximativă", type="time"),
    PersonalField(key="lost_money", label="Am pierdut bani", type="checkbox"),
    PersonalField(key="amount_lost", label="Suma pierdută (lei)", type="number"),
    PersonalField(key="bank", label="Banca dumneavoastră", type="text"),
    PersonalField(key="additional_details", label="Alte detalii", type="textarea"),
]


class FraudReportDraft(BaseModel):
    report_id: UUID
    generated_at: datetime
    recipient: str = Field(description="where 'Trimite e-mail' sends it (demo inbox)")
    incident: Incident
    personal_data: PersonalData = Field(default_factory=PersonalData)
    personal_fields: list[PersonalField] = Field(default_factory=lambda: list(PERSONAL_FIELDS))


class ReportPdfRequest(BaseModel):
    report: FraudReportDraft
    personal_data: PersonalData = Field(default_factory=PersonalData)


class ReportSendRequest(BaseModel):
    report: FraudReportDraft
    personal_data: PersonalData

    @model_validator(mode="after")
    def _minimum_identity(self) -> "ReportSendRequest":
        p = self.personal_data
        missing = []
        if not p.last_name:
            missing.append("numele")
        if not p.first_name:
            missing.append("prenumele")
        if not (p.phone or p.email):
            missing.append("un telefon sau un e-mail")
        if missing:
            raise ValueError("Vă rugăm completați " + ", ".join(missing) + ".")
        return self


class ReportSendResponse(BaseModel):
    sent: bool
    recipient: str
    message_id: str
    sent_at: datetime
