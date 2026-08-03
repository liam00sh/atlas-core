"""Contrato común para proveedores de texto a voz."""

from __future__ import annotations

from abc import ABC, abstractmethod

from voice.models import SynthesisRequest, SynthesisResult


class BaseTTSProvider(ABC):
    """Interfaz que deben implementar todos los proveedores TTS."""

    provider_id: str

    @abstractmethod
    def is_available(self) -> bool:
        """Indica si el proveedor está preparado para sintetizar."""

    @abstractmethod
    def supports_voice(self, provider_voice_id: str) -> bool:
        """Indica si el proveedor admite una voz concreta."""

    @abstractmethod
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Convierte texto en audio y devuelve un resultado normalizado."""
