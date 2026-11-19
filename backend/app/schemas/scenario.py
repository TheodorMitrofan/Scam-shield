"""Input DTOs — the official scenario format from the brief (CLAUDE.md §4.2).

Field names must match the JSON files exactly; do not rename. Parsing is lenient on content
(empty / emoji-only / very long text must never crash) but strict on structure.
"""

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_serializer


class Channel(StrEnum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    CHAT = "chat"
    CALL_TRANSCRIPT = "call_transcript"


class Author(StrEnum):
    SENDER = "sender"
    READER = "reader"


class _Dto(BaseModel):
    # Ignore unknown fields so a slightly different test-set file never breaks loading.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)


class _DropUnsetExtensions(BaseModel):
    """Our stage-4 extension fields are omitted from JSON when unset, so every output (API, detector
    input, DB) stays byte-for-byte the official format. Official nulls like `sender.name` are kept."""

    _extensions: ClassVar[tuple[str, ...]] = ()

    @model_serializer(mode="wrap")
    def _drop(self, handler):
        d = handler(self)
        for k in self._extensions:
            if d.get(k) is None:
                d.pop(k, None)
        return d


class Sender(_Dto):
    name: str | None = None
    address: str | None = None
    known_contact: bool = False


class Message(_DropUnsetExtensions):
    _extensions = ("start_s", "end_s")

    n: int = Field(ge=1, description="1-based position in the thread, reader replies included")
    from_: Author = Field(alias="from")
    text: str = ""
    # Stage 4 extension: utterance position inside the audio file.
    start_s: float | None = Field(default=None, ge=0)
    end_s: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VoiceLocation(_Dto):
    region: str
    confidence: float = Field(ge=0, le=1)


class AudioRef(_DropUnsetExtensions):
    """Stage 4 extension: links a scenario to an uploaded audio file (stored on disk, see db.models.AudioFile)."""

    _extensions = ("location",)

    audio_id: str
    mime: str
    duration_s: float = Field(ge=0)
    location: VoiceLocation | None = None


class Scenario(_DropUnsetExtensions):
    _extensions = ("audio",)
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    channel: Channel
    sender: Sender = Field(default_factory=Sender)
    messages: list[Message] = Field(default_factory=list)
    audio: AudioRef | None = None

    def to_detector_input(self) -> dict:
        """Plain dict in the official JSON shape — what `scam_detector.analyze()` receives."""
        return self.model_dump(mode="json", by_alias=True)
