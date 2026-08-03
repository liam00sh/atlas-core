"""Síntesis y preparación de notas de voz para Telegram."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile

from voice.models import AssistantIdentity
from voice.preferences.manager import VoicePreferenceManager
from voice.runtime import build_voice_service


@dataclass(frozen=True, slots=True)
class TelegramVoiceResult:
    success: bool
    ogg_path: Path | None
    error: str | None = None


class TelegramVoiceRenderer:
    """Genera OGG/Opus a partir de una respuesta textual."""

    def __init__(
        self,
        *,
        project_root: Path,
        user_provider,
        personality_provider,
        ffmpeg_path: str | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.user_provider = user_provider
        self.personality_provider = personality_provider
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        self.voice_service = build_voice_service()
        self.preferences = VoicePreferenceManager(
            storage_path=(
                self.project_root
                / "data"
                / "voice"
                / "user_preferences.json"
            ),
            user_provider=user_provider,
        )
        self.output_dir = (
            self.project_root
            / "data"
            / "telegram_voice"
            / "out"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return self.voice_service is not None and bool(self.ffmpeg_path)

    def render(self, text: str) -> TelegramVoiceResult:
        if not self.is_available():
            return TelegramVoiceResult(
                False,
                None,
                "TTS o FFmpeg no disponible.",
            )

        identity_name = str(self.personality_provider()).strip().casefold()
        identity = (
            AssistantIdentity.COCO
            if identity_name == "coco"
            else AssistantIdentity.DAXTER
        )
        preferences = self.preferences.get_current()
        result = self.voice_service.speak(
            text,
            identity=identity,
            preferences=preferences,
            speed=preferences.speech_rate,
            volume=preferences.speech_volume,
        )

        if not result.success or result.output_path is None:
            return TelegramVoiceResult(
                False,
                None,
                result.error or "No se pudo sintetizar la respuesta.",
            )

        wav_path = Path(result.output_path)
        if not wav_path.exists():
            return TelegramVoiceResult(
                False,
                None,
                "La síntesis no produjo un archivo reproducible.",
            )

        with tempfile.NamedTemporaryFile(
            prefix="atlas_telegram_",
            suffix=".ogg",
            dir=self.output_dir,
            delete=False,
        ) as temporary:
            ogg_path = Path(temporary.name)

        command = [
            str(self.ffmpeg_path),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-c:a",
            "libopus",
            "-b:a",
            "48k",
            "-vbr",
            "on",
            "-application",
            "voip",
            str(ogg_path),
        ]

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            ogg_path.unlink(missing_ok=True)
            return TelegramVoiceResult(False, None, str(exc))

        if completed.returncode != 0 or not ogg_path.exists():
            ogg_path.unlink(missing_ok=True)
            message = completed.stderr.strip() or "FFmpeg falló."
            return TelegramVoiceResult(False, None, message)

        return TelegramVoiceResult(True, ogg_path)

    @staticmethod
    def cleanup(result: TelegramVoiceResult) -> None:
        if result.ogg_path is not None:
            result.ogg_path.unlink(missing_ok=True)
