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
_PHONE = re.compile(r"^\+?[\d\s.\-()]{10,20}$")
_ID_CARD = re.compile(r"^([A-Za-z]{2})\s*(\d{6})$")  # Romanian ID card: series (2 letters) + number (6 digits)

# Required to file the complaint (same list drives the UI form via PERSONAL_FIELDS).
REQUIRED_PERSONAL = {
    "last_name": "numele",
    "first_name": "prenumele",
    "cnp": "CNP-ul",
    "id_series_number": "seria și numărul actului de identitate",
    "address": "adresa de domiciliu",
    "phone": "telefonul",
    "email": "e-mailul",
    "incident_date": "data incidentului",
    "incident_time": "ora incidentului",
}


class PersonalData(BaseModel):
    """Filled in by the user. Empty in the draft; `missing_required()` is enforced before PDF / send."""

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

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not _PHONE.match(v) or sum(c.isdigit() for c in v) < 10:
            raise ValueError("Numărul de telefon nu pare corect (ex.: 0722 123 456).")
        return v

    @field_validator("id_series_number")
    @classmethod
    def _id_card_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        m = _ID_CARD.match(v.strip())
        if not m:
            raise ValueError("Seria și numărul actului: 2 litere și 6 cifre (ex.: RX 123456).")
        return f"{m.group(1).upper()} {m.group(2)}"

    @field_validator("incident_date")
    @classmethod
    def _not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Data incidentului nu poate fi în viitor.")
        return v

    def missing_required(self) -> list[str]:
        return [label for key, label in REQUIRED_PERSONAL.items() if getattr(self, key) in (None, "")]


PERSONAL_FIELDS: list[PersonalField] = [
    PersonalField(key="last_name", label="Nume", type="text", required=True),
    PersonalField(key="first_name", label="Prenume", type="text", required=True),
    PersonalField(key="cnp", label="CNP", type="text", required=True, hint="13 cifre"),
    PersonalField(key="id_series_number", label="Seria și numărul actului de identitate", type="text",
                  required=True, hint="Ex.: RX 123456"),
    PersonalField(key="address", label="Adresa de domiciliu", type="text", required=True,
                  hint="Localitate, stradă, nr., bloc, scară, etaj, ap., județ / sector"),
    PersonalField(key="phone", label="Telefon", type="tel", required=True, hint="Ex.: 0722 123 456"),
    PersonalField(key="email", label="E-mail", type="email", required=True),
    PersonalField(key="incident_date", label="Data la care ați primit mesajul", type="date", required=True),
    PersonalField(key="incident_time", label="Ora aproximativă", type="time", required=True),
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


def _require_complete(p: PersonalData) -> None:
    missing = p.missing_required()
    if missing:
        raise ValueError("Vă rugăm completați: " + ", ".join(missing) + ".")


class ReportPdfRequest(BaseModel):
    report: FraudReportDraft
    personal_data: PersonalData

    @model_validator(mode="after")
    def _complete(self) -> "ReportPdfRequest":
        _require_complete(self.personal_data)
        return self


class ReportSendRequest(BaseModel):
    report: FraudReportDraft
    personal_data: PersonalData

    @model_validator(mode="after")
    def _complete(self) -> "ReportSendRequest":
        _require_complete(self.personal_data)
        return self


class ReportSendResponse(BaseModel):
    sent: bool
    recipient: str
    message_id: str
    sent_at: datetime
