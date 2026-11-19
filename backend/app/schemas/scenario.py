"""Input DTOs — the official scenario format from the brief (CLAUDE.md §4.2).

Field names must match the JSON files exactly; do not rename. Parsing is lenient on content
(empty / emoji-only / very long text must never crash) but strict on structure.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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


class Sender(_Dto):
    name: str | None = None
    address: str | None = None
    known_contact: bool = False


class Message(_Dto):
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


class AudioRef(_Dto):
    """Stage 4 extension: links a scenario to an uploaded audio file (stored on disk, see db.models.AudioFile)."""

    audio_id: str
    mime: str
    duration_s: float = Field(ge=0)
    location: VoiceLocation | None = None


class Scenario(_Dto):
    id: str = Field(min_length=1)
    channel: Channel
    sender: Sender = Field(default_factory=Sender)
    messages: list[Message] = Field(default_factory=list)
    audio: AudioRef | None = None

    def to_detector_input(self) -> dict:
        """Plain dict in the official JSON shape — what `scam_detector.analyze()` receives.

        Official nulls (e.g. `sender.name: null`) are kept; our optional extensions are dropped when unset.
        """
        d = self.model_dump(mode="json", by_alias=True)
        if d.get("audio") is None:
            d.pop("audio", None)
        for m in d["messages"]:
            for k in ("start_s", "end_s"):
                if m.get(k) is None:
                    m.pop(k, None)
        return d
