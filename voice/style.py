"""Selección de emoción e intensidad independiente del proveedor TTS."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class VoiceIntensity(StrEnum):
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"


class VoiceEnergy(StrEnum):
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"


@dataclass(frozen=True, slots=True)
class DaxterVoiceStyle:
    emotion: str
    intensity: VoiceIntensity
    energy: VoiceEnergy
    reason: str
    style_key: str


class VoiceStyleSelector:
    """Resuelve una intención emocional sin conocer Chatterbox."""

    def __init__(self, catalog_path: Path):
        payload = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        self._emotions = {item["id"]: item for item in payload["emotions"]}
        if "neutral" not in self._emotions:
            raise ValueError("El catálogo necesita un fallback neutral")

    @staticmethod
    def _intensity(value: str | VoiceIntensity) -> VoiceIntensity:
        try:
            return VoiceIntensity(str(value))
        except ValueError:
            return VoiceIntensity.MEDIUM

    @staticmethod
    def _energy(value: str | VoiceEnergy | None, fallback: str) -> VoiceEnergy:
        try:
            return VoiceEnergy(str(value or fallback))
        except ValueError:
            return VoiceEnergy.MEDIUM

    def resolve(
        self,
        emotion: str,
        intensity: str | VoiceIntensity = VoiceIntensity.MEDIUM,
        energy: str | VoiceEnergy | None = None,
    ) -> DaxterVoiceStyle:
        requested = str(emotion or "neutral").strip().casefold()
        reason_parts = []
        if requested not in self._emotions:
            requested = "neutral"
            reason_parts.append("emoción desconocida; fallback neutral")
        item = self._emotions[requested]
        resolved_intensity = self._intensity(intensity)
        supported = [VoiceIntensity(value) for value in item["supported_intensities"]]
        if resolved_intensity not in supported:
            order = {VoiceIntensity.LOW: 0, VoiceIntensity.MEDIUM: 1, VoiceIntensity.HIGH: 2}
            resolved_intensity = min(supported, key=lambda value: abs(order[value] - order[resolved_intensity]))
            reason_parts.append("intensidad no soportada; se usó la más próxima")
        resolved_energy = self._energy(energy, item["preferred_energy"])
        if not reason_parts:
            reason_parts.append("estilo definido por catálogo; validación humana pendiente")
        return DaxterVoiceStyle(
            emotion=requested,
            intensity=resolved_intensity,
            energy=resolved_energy,
            reason="; ".join(reason_parts),
            style_key=f"daxter:{requested}:{resolved_intensity.value}",
        )
