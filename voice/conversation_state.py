"""Estado efímero y explícito de una sesión de voz."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VoiceConfirmationState(StrEnum):
    NONE = "none"
    TRANSCRIPT_CONFIRMATION = "transcript_confirmation"
    ACTION_CONFIRMATION = "action_confirmation"
    DANGEROUS_ACTION_CONFIRMATION = "dangerous_action_confirmation"


@dataclass(slots=True)
class PendingTranscriptConfirmation:
    raw_transcript: str
    normalized_transcript: str


@dataclass(slots=True)
class VoiceConversationMemory:
    last_user_utterance: str = ""
    last_raw_transcript: str = ""
    last_normalized_transcript: str = ""
    last_base_response: str = ""
    last_styled_response: str = ""
    last_spoken_response: str = ""

    def public_trace(self) -> dict[str, str]:
        return {
            "last_user_utterance": self.last_user_utterance,
            "last_raw_transcript": self.last_raw_transcript,
            "last_normalized_transcript": self.last_normalized_transcript,
            "last_base_response": self.last_base_response,
            "last_styled_response": self.last_styled_response,
            "last_spoken_response": self.last_spoken_response,
        }
