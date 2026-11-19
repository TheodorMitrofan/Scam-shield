"""Output DTOs — what the detector (`scam_detector.analyze`) must return (CLAUDE.md §4.2).

The backend validates every detector response against `AnalysisResult`, so a contract break
on the ML side shows up as a clear error here instead of a broken UI.
Codes and bands mirror Scam_Shield_Public_Kit/official_catalog.json.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Verdict(StrEnum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    SCAM = "SCAM"


class RedFlag(StrEnum):
    CODE_REQUEST = "RF_CODE_REQUEST"
    REMOTE_ACCESS = "RF_REMOTE_ACCESS"
    DATA_REQUEST = "RF_DATA_REQUEST"
    PAYMENT_REQUEST = "RF_PAYMENT_REQUEST"
    SUSPICIOUS_CONTACT = "RF_SUSPICIOUS_CONTACT"
    NEW_NUMBER = "RF_NEW_NUMBER"
    SECRECY = "RF_SECRECY"
    TOO_GOOD = "RF_TOO_GOOD"
    IMPERSONATION = "RF_IMPERSONATION"
    URGENCY = "RF_URGENCY"
    THREAT = "RF_THREAT"
    EMOTIONAL_PRESSURE = "RF_EMOTIONAL_PRESSURE"
    CHANNEL_SWITCH = "RF_CHANNEL_SWITCH"


class ScamType(StrEnum):
    BANK_IMPERSONATION = "BANK_IMPERSONATION"
    COURIER_FEE = "COURIER_FEE"
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    FAMILY_EMERGENCY = "FAMILY_EMERGENCY"
    TECH_SUPPORT = "TECH_SUPPORT"
    MARKETPLACE = "MARKETPLACE"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    INVESTMENT = "INVESTMENT"
    ROMANCE = "ROMANCE"
    JOB_OFFER = "JOB_OFFER"
    PRIZE_LOTTERY = "PRIZE_LOTTERY"
    OTHER = "OTHER"
    NONE = "NONE"


RED_FLAG_POINTS: dict[RedFlag, int] = {
    RedFlag.CODE_REQUEST: 35,
    RedFlag.REMOTE_ACCESS: 35,
    RedFlag.DATA_REQUEST: 30,
    RedFlag.PAYMENT_REQUEST: 25,
    RedFlag.SUSPICIOUS_CONTACT: 25,
    RedFlag.NEW_NUMBER: 20,
    RedFlag.SECRECY: 20,
    RedFlag.TOO_GOOD: 20,
    RedFlag.IMPERSONATION: 15,
    RedFlag.URGENCY: 15,
    RedFlag.THREAT: 15,
    RedFlag.EMOTIONAL_PRESSURE: 10,
    RedFlag.CHANNEL_SWITCH: 10,
}


def verdict_for(score: int) -> Verdict:
    """Official bands: 0–24 SAFE, 25–49 SUSPICIOUS, 50–100 SCAM."""
    if score >= 50:
        return Verdict.SCAM
    if score >= 25:
        return Verdict.SUSPICIOUS
    return Verdict.SAFE


def score_for(flags: list[RedFlag] | set[RedFlag]) -> int:
    """Sum of unique flag points, capped at 100."""
    return min(100, sum(RED_FLAG_POINTS[f] for f in set(flags)))


class _Dto(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MessageFlags(_Dto):
    n: int = Field(ge=1)
    flags: list[RedFlag] = Field(default_factory=list, description="flags first detected in message n")
    score_after: int = Field(ge=0, le=100, description="cumulative score of the prefix 1..n")


class WarningText(_Dto):
    ro: str
    en: str | None = None


class Evidence(_Dto):
    n: int = Field(ge=1)
    flag: RedFlag
    span: tuple[int, int] = Field(description="[start, end) char offsets in message n's text")


class AnalysisResult(_Dto):
    id: str
    verdict: Verdict
    scam_type: ScamType
    risk_score: int = Field(ge=0, le=100)
    first_alert: int | None = Field(default=None, ge=1)
    red_flags: list[RedFlag] = Field(default_factory=list)
    flags_by_message: list[MessageFlags] = Field(default_factory=list)
    warning: WarningText
    evidence: list[Evidence] | None = None

    @model_validator(mode="after")
    def _apply_official_formula(self) -> "AnalysisResult":
        # The detector decides *which* flags fire; score, verdict and the SAFE invariants are
        # deterministic (official formula), so we normalise them here instead of failing the request.
        self.red_flags = list(dict.fromkeys(self.red_flags))
        self.risk_score = score_for(self.red_flags)
        self.verdict = verdict_for(self.risk_score)
        if self.verdict == Verdict.SAFE:
            self.scam_type = ScamType.NONE
            self.first_alert = None
        elif self.scam_type == ScamType.NONE:
            self.scam_type = ScamType.OTHER  # risky but untyped → official fallback type
        return self
