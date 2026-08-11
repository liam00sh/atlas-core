"""Modelos compartidos del subsistema de voz."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping

class AssistantIdentity(StrEnum):
    DAXTER = "daxter"
    COCO = "coco"

@dataclass(frozen=True, slots=True)
class VoiceDefinition:
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
    requested_voice_id: str
    selected_voice_id: str | None
    fallback_used: bool
    reason: str

@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    text: str
    voice_id: str
    provider_voice_id: str
    output_path: Path
    speed: float = 1.0
    volume: float = 1.0
    emotion: str = "neutral"
    intensity: str = "media"
    voice_profile_id: str | None = None
    profile_version: str | None = None

@dataclass(frozen=True, slots=True)
class SynthesisResult:
    success: bool
    output_path: Path | None
    voice_id: str
    provider_id: str
    error: str | None = None
    requested_voice_id: str | None = None
    fallback_used: bool = False
    selection_reason: str | None = None
    cache_hit: bool = False
    latency_ms: float | None = None
    emotion: str | None = None
    intensity: str | None = None
