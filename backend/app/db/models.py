"""PostgreSQL tables (SQLAlchemy 2.0). Rows exist ONLY when the user consented to saving.

- analysis_records: one saved analysis. Indexed columns for listing; the full conversation and
  result are JSONB so the DTOs can evolve without migrations during the hackathon.
- audio_files (stage 5): metadata only. The audio bytes live on disk under STORAGE_DIR, never in the DB.
Both tables have `expires_at`; a cleanup job deletes expired rows (and their files).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    path: Mapped[str] = mapped_column(String(512), comment="relative to STORAGE_DIR")
    mime: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Float)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Denormalised from `result` for listing/filtering without parsing JSON.
    scenario_id: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(32))
    verdict: Mapped[str] = mapped_column(String(16), index=True)
    scam_type: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[int] = mapped_column(Integer)
    first_alert: Mapped[int | None] = mapped_column(Integer)
    red_flags: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)

    # Full payloads (Scenario / AnalysisResult DTOs, JSON mode). Contain message text → consent only.
    scenario: Mapped[dict] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB)

    audio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="SET NULL")
    )
    audio: Mapped[AudioFile | None] = relationship()
