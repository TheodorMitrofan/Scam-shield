"""Database schema — hybrid model (CLAUDE.md §7).

Relational hierarchy for what every channel has:
    applications ─┬─ contacts ─── conversations ─── messages
                  └──────────────┘ (conversation also points to its application)
EAV for what only some applications have (email subject, audio timestamps, voice region, ...):
    attribute_definitions (application, entity, name, type) + attribute_values (entity_id, value)

Rows exist ONLY when the user ticked the consent checkbox (`save=true`). Everything is scoped by
`client_id` (anonymous browser UUID) and conversations expire (`expires_at`).
Portable types (Uuid / JSON) so tests run on SQLite; JSON becomes JSONB on PostgreSQL.
Audio bytes live on disk (STORAGE_DIR); `audio_files` holds metadata only.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    """One row per channel/app: sms, whatsapp, email, chat, call_transcript (seeded at startup)."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(64))
    view_kind: Mapped[str] = mapped_column(String(16), comment="chat | email | call — how the UI renders it")

    contacts: Mapped[list["Contact"]] = relationship(back_populates="application")


class Contact(Base):
    """A sender as seen in one application by one user (same address in the same app = same contact)."""

    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("client_id", "application_id", "address", name="uq_contact_per_app"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    address: Mapped[str] = mapped_column(String(255), comment="phone / e-mail / username; '' if unknown")
    display_name: Mapped[str | None] = mapped_column(String(255))
    known_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _now()

    application: Mapped[Application] = relationship(back_populates="contacts")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )


class Conversation(Base):
    """One analysed scenario (thread) with a contact, plus the detector's verdict."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("client_id", "contact_id", "external_id", name="uq_conversation_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(64), comment="scenario id from the file, e.g. V04 / PASTE")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    verdict: Mapped[str] = mapped_column(String(16), index=True)
    scam_type: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[int] = mapped_column(Integer)
    first_alert: Mapped[int | None] = mapped_column(Integer)
    red_flags: Mapped[list[str]] = mapped_column(JsonType, default=list)
    warning_ro: Mapped[str] = mapped_column(Text)
    warning_en: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list | None] = mapped_column(JsonType)

    contact: Mapped[Contact] = relationship(back_populates="conversations")
    application: Mapped[Application] = relationship()
    messages: Mapped[list["MessageRow"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MessageRow.n",
    )


class MessageRow(Base):
    """One message of a conversation, with the flags the detector found in it."""

    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "n", name="uq_message_n"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    n: Mapped[int] = mapped_column(Integer)
    author: Mapped[str] = mapped_column(String(8), comment="sender | reader")
    text: Mapped[str] = mapped_column(Text)
    flags: Mapped[list[str]] = mapped_column(JsonType, default=list)
    score_after: Mapped[int] = mapped_column(Integer, default=0)
    is_first_alert: Mapped[bool] = mapped_column(Boolean, default=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AttributeDefinition(Base):
    """EAV schema: which extra attribute an entity of an application may have.

    `application_id` NULL = applies to every application.
    """

    __tablename__ = "attribute_definitions"
    __table_args__ = (UniqueConstraint("application_id", "entity", "name", name="uq_attribute_def"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"))
    entity: Mapped[str] = mapped_column(String(16), comment="contact | conversation | message")
    name: Mapped[str] = mapped_column(String(64))
    data_type: Mapped[str] = mapped_column(String(8), comment="text | number | json")


class AttributeValue(Base):
    """EAV value. `entity_id` is the id of a contact / conversation / message row."""

    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "entity_id", name="uq_attribute_value"),
        Index("ix_attribute_values_entity", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attribute_definitions.id", ondelete="CASCADE"))
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Float)
    value_json: Mapped[dict | list | None] = mapped_column(JsonType)

    attribute: Mapped[AttributeDefinition] = relationship()


class AudioFile(Base):
    """Stage 5: metadata of an uploaded audio file; bytes are on disk under STORAGE_DIR."""

    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    path: Mapped[str] = mapped_column(String(512), comment="relative to STORAGE_DIR")
    mime: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Float)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = _now()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


# Seed data -------------------------------------------------------------------------------------

APPLICATIONS = [
    ("sms", "SMS", "chat"),
    ("whatsapp", "WhatsApp", "chat"),
    ("email", "E-mail", "email"),
    ("chat", "Chat", "chat"),
    ("call_transcript", "Apel telefonic", "call"),
]

# (application code or None for all, entity, name, data_type)
ATTRIBUTES = [
    ("email", "conversation", "subject", "text"),
    (None, "message", "start_s", "number"),
    (None, "message", "end_s", "number"),
    ("call_transcript", "conversation", "audio_id", "text"),
    ("call_transcript", "conversation", "audio_mime", "text"),
    ("call_transcript", "conversation", "audio_duration_s", "number"),
    ("call_transcript", "conversation", "voice_region", "text"),
    ("call_transcript", "conversation", "voice_confidence", "number"),
]
