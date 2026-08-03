"""Modelos compartidos del subsistema de voz."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping


class AssistantIdentity(StrEnum):
    """Identidades de asistente compatibles."""

    DAXTER = "daxter"
    COCO = "coco"


@dataclass(frozen=True, slots=True)
class VoiceDefinition:
    """Describe una voz disponible sin acoplarla a un motor concreto."""

    voice_id: str
    display_name: str
    identity: AssistantIdentity
    provider_id: str
    provider_voice_id: str
    language: str
    region: str
    is_official: bool
    enabled: bool = True
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VoiceSelection:
    """Resultado de resolver la voz que debe utilizar Atlas."""

    requested_voice_id: str
    selected_voice_id: str | None
    fallback_used: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    """Petición normalizada de síntesis."""

    text: str
    voice_id: str
    provider_voice_id: str
    output_path: Path
    speed: float = 1.0
    volume: float = 1.0


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    """Resultado normalizado de una síntesis de voz."""

    success: bool
    output_path: Path | None
    voice_id: str
    provider_id: str
    error: str | None = None
