"""DTO ⇄ ORM conversion, kept in one place so routes never touch ORM objects directly."""

from datetime import UTC, datetime, timedelta

from app.schemas import AnalysisResult, HistoryCreate, HistoryItemDetail, Scenario

from .models import AnalysisRecord


def record_from_dto(dto: HistoryCreate) -> AnalysisRecord:
    r = dto.result
    return AnalysisRecord(
        client_id=dto.client_id,
        expires_at=datetime.now(UTC) + timedelta(hours=dto.retention_hours),
        scenario_id=dto.scenario.id,
        channel=dto.scenario.channel.value,
        verdict=r.verdict.value,
        scam_type=r.scam_type.value,
        risk_score=r.risk_score,
        first_alert=r.first_alert,
        red_flags=[f.value for f in r.red_flags],
        scenario=dto.scenario.to_detector_input(),
        result=r.model_dump(mode="json", exclude_none=True),
        audio_id=dto.audio_id,
    )


def detail_from_record(rec: AnalysisRecord) -> HistoryItemDetail:
    return HistoryItemDetail(
        id=rec.id,
        created_at=rec.created_at,
        expires_at=rec.expires_at,
        scenario_id=rec.scenario_id,
        channel=rec.channel,
        verdict=rec.verdict,
        scam_type=rec.scam_type,
        risk_score=rec.risk_score,
        first_alert=rec.first_alert,
        scenario=Scenario.model_validate(rec.scenario),
        result=AnalysisResult.model_validate(rec.result),
        audio_id=rec.audio_id,
    )
