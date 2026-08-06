"""Síntesis Telegram sin reproducción local y con temporales controlados."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import shutil
import subprocess
from time import perf_counter

from voice.models import AssistantIdentity


@dataclass(frozen=True, slots=True)
class TelegramVoiceResult:
    success: bool
    ogg_path: Path | None
    error: str | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)


class TelegramVoiceRenderer:
    def __init__(self, *, voice_service, preference_resolver, personality_resolver, output_dir: str | Path, ffmpeg_path: str | None = None, timeout_seconds: float = 60.0) -> None:
        self.voice_service = voice_service
        self.preference_resolver = preference_resolver
        self.personality_resolver = personality_resolver
        self.output_dir = Path(output_dir)
        self.ffmpeg_path = shutil.which("ffmpeg") if ffmpeg_path is None else ffmpeg_path
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        provider = getattr(self.voice_service, "provider", None)
        return bool(self.ffmpeg_path and provider is not None and provider.is_available())

    def render(self, text: str, *, user_id: str) -> TelegramVoiceResult:
        if not self.is_available():
            return TelegramVoiceResult(False, None, "TTS o FFmpeg no disponible.")
        identity = AssistantIdentity.COCO if str(self.personality_resolver(user_id)).casefold() == "coco" else AssistantIdentity.DAXTER
        preferences = self.preference_resolver(user_id)
        timings: dict[str, float] = {}
        started = perf_counter()
        result = self.voice_service.speak(
            text,
            identity=identity,
            preferences=preferences,
            speed=preferences.speech_rate,
            volume=preferences.speech_volume,
            play_audio=False,
        )
        timings["tts.synthesize"] = round((perf_counter() - started) * 1000, 3)
        wav_path = Path(result.output_path) if result.output_path is not None else None
        if not result.success or wav_path is None or not wav_path.is_file():
            self._unlink(wav_path)
            return TelegramVoiceResult(False, None, result.error or "La síntesis no produjo un WAV.", timings)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ogg_path = self.output_dir / f"voice_{os.urandom(16).hex()}.ogg"
        command = [
            str(self.ffmpeg_path), "-nostdin", "-v", "error", "-y", "-i", str(wav_path),
            "-c:a", "libopus", "-b:a", "48k", "-vbr", "on", "-application", "voip", str(ogg_path),
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            self._unlink(ogg_path)
            return TelegramVoiceResult(False, None, "FFmpeg no pudo preparar la nota de voz.", timings)
        finally:
            self._unlink(wav_path)
        if completed.returncode != 0 or not ogg_path.is_file():
            self._unlink(ogg_path)
            return TelegramVoiceResult(False, None, "FFmpeg no pudo preparar la nota de voz.", timings)
        return TelegramVoiceResult(True, ogg_path, timings_ms=timings)

    @classmethod
    def cleanup(cls, result: TelegramVoiceResult) -> None:
        cls._unlink(result.ogg_path)

    @staticmethod
    def _unlink(path: Path | None) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
