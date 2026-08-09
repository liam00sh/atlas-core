"""Jerarquía explícita de fuentes de verdad gobernada por Atlas."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class TruthSource(StrEnum):
    TOOL_STATE = "tool_state"
    VERIFIED_PERSONAL = "verified_personal"
    AUTHENTICATED_IDENTITY = "authenticated_identity"
    CONVERSATION_CONTEXT = "conversation_context"
    PERSISTENT_MEMORY = "persistent_memory"
    AUTHORIZED_WEB = "authorized_web"
    MODEL_INFERENCE = "model_inference"


class TruthPriority(IntEnum):
    TOOL_STATE = 700
    VERIFIED_PERSONAL = 600
    AUTHENTICATED_IDENTITY = 500
    CONVERSATION_CONTEXT = 400
    PERSISTENT_MEMORY = 300
    AUTHORIZED_WEB = 200
    MODEL_INFERENCE = 100


PRIORITY_BY_SOURCE = {
    TruthSource.TOOL_STATE: TruthPriority.TOOL_STATE,
    TruthSource.VERIFIED_PERSONAL: TruthPriority.VERIFIED_PERSONAL,
    TruthSource.AUTHENTICATED_IDENTITY: TruthPriority.AUTHENTICATED_IDENTITY,
    TruthSource.CONVERSATION_CONTEXT: TruthPriority.CONVERSATION_CONTEXT,
    TruthSource.PERSISTENT_MEMORY: TruthPriority.PERSISTENT_MEMORY,
    TruthSource.AUTHORIZED_WEB: TruthPriority.AUTHORIZED_WEB,
    TruthSource.MODEL_INFERENCE: TruthPriority.MODEL_INFERENCE,
}


@dataclass(frozen=True, slots=True)
class TruthClaim:
    subject: str
    predicate: str
    value: object
    source: TruthSource
    verified: bool = False


@dataclass(frozen=True, slots=True)
class TruthResolution:
    claim: TruthClaim | None
    conflict: bool
    sufficient: bool
    reason: str


class TruthResolver:
    """Prioriza estructura y estado real; nunca asciende una inferencia a hecho."""

    def resolve(self, claims: list[TruthClaim]) -> TruthResolution:
        if not claims:
            return TruthResolution(None, False, False, "no_information")
        ordered = sorted(
            claims,
            key=lambda item: (PRIORITY_BY_SOURCE[item.source], bool(item.verified)),
            reverse=True,
        )
        winner = ordered[0]
        same_authority = [
            item for item in ordered
            if PRIORITY_BY_SOURCE[item.source] == PRIORITY_BY_SOURCE[winner.source]
        ]
        conflicting = any(item.value != winner.value for item in same_authority[1:])
        if conflicting:
            return TruthResolution(None, True, False, "unresolved_equal_priority_conflict")
        if winner.source is TruthSource.MODEL_INFERENCE and not winner.verified:
            return TruthResolution(winner, False, False, "inference_only")
        return TruthResolution(winner, False, True, f"selected:{winner.source.value}")

