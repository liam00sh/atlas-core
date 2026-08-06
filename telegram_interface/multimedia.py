"""Orquestación multimedia: analiza una vez y entrega el resultado al núcleo normal."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from telegram_interface.models import TelegramMessage, TelegramRequestContext
from voice.stt import STTError, STTService


@dataclass(frozen=True, slots=True)
class MultimediaResult:
    text: str
    timings_ms: dict[str, float] = field(default_factory=dict)
    input_language: str | None = None


class TelegramMultimediaProcessor:
    def __init__(
        self,
        *,
        stt: STTService | None = None,
        language_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        self.stt = stt
        self.language_resolver = language_resolver or (lambda _user: None)

    def process(self, message: TelegramMessage, context: TelegramRequestContext, core) -> MultimediaResult | None:
        if message.media_type not in {"voice", "audio"}:
            return None
        if self.stt is None:
            return MultimediaResult(
                "No puedo transcribir este audio porque el reconocimiento de voz local no está configurado."
            )
        if message.media_status != "quarantined" or not message.local_path:
            return None
        try:
            transcript, timings = self.stt.transcribe(
                Path(message.local_path),
                language_hint=self.language_resolver(context.atlas_user_id or ""),
            )
        except STTError as exc:
            messages = {
                "stt_unavailable": "No puedo transcribir este audio porque el reconocimiento de voz local no está disponible.",
                "stt_timeout": "La transcripción ha tardado demasiado y se ha cancelado.",
                "audio_too_long": "El audio supera la duración segura configurada.",
                "audio_empty": "No he detectado voz utilizable en el audio.",
                "audio_corrupt": "El audio está dañado o usa un formato que no se puede convertir.",
                "ffmpeg_unavailable": "No puedo convertir el audio porque FFmpeg no está disponible.",
            }
            return MultimediaResult(messages.get(exc.code, "No he podido transcribir el audio de forma segura."))

        # La transcripción entra exactamente una vez en el mismo adaptador que
        # el texto. No se crea historial, memoria ni segunda inteligencia aquí.
        response = core.process(transcript.text, context)
        return MultimediaResult(str(response), timings, transcript.language)
