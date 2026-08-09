"""Servicio de alto nivel para resolver, sintetizar y reproducir voz."""
from __future__ import annotations
import re, time
from pathlib import Path
from voice.catalog.voices import VOICE_CATALOG
from voice.config import COCO_PREFERRED_VOICE, DAXTER_PREFERRED_VOICE, VOICE_OUTPUT_DIR
from voice.models import AssistantIdentity, SynthesisRequest, SynthesisResult
from voice.player import WavePlayer
from voice.preferences.voice_preferences import VoicePreferences
from voice.providers.kokoro_provider import KokoroProvider
from voice.resolver.voice_resolver import VoiceResolver
from voice.text_normalizer import normalize_for_tts

class VoiceService:
    def __init__(self, *, provider=None, player=None, output_dir=None) -> None:
        self.provider = provider or KokoroProvider()
        self.player = player or WavePlayer()
        self.output_dir = output_dir or VOICE_OUTPUT_DIR
        self.resolver = VoiceResolver(availability_check=self._is_voice_available)

    def is_available(self) -> bool:
        return self.provider.is_available() and self.player.is_available()

    def preferred_voice(self, identity, preferences=None) -> str:
        if preferences is not None:
            return preferences.preferred_voice_for(identity)
        return COCO_PREFERRED_VOICE if identity is AssistantIdentity.COCO else DAXTER_PREFERRED_VOICE

    def speak(self, text: str, *, identity, requested_voice_id=None,
              preferences=None, speed=1.0, volume=1.0,
              play_audio=True) -> SynthesisResult:
        total_started = time.perf_counter()
        prepare_started = time.perf_counter()
        identity = AssistantIdentity(identity)
        clean_text = normalize_for_tts(self.clean_console_text(text))
        requested = requested_voice_id or self.preferred_voice(identity, preferences)
        timings = {
            "tts.prepare": round((time.perf_counter() - prepare_started) * 1000, 3),
        }
        if not clean_text:
            return SynthesisResult(False, None, requested, "none",
                                   "No hay texto reproducible.",
                                   requested_voice_id=requested,
                                   timings_ms=timings)

        selection = self.resolver.resolve(
            identity=identity,
            requested_voice_id=requested,
            fallback_enabled=preferences.fallback_enabled if preferences else True,
        )
        if selection.selected_voice_id is None:
            return SynthesisResult(False, None, requested, "none",
                                   selection.reason,
                                   requested_voice_id=requested,
                                   selection_reason=selection.reason,
                                   timings_ms=timings)

        definition = VOICE_CATALOG[selection.selected_voice_id]
        output_path = self._build_output_path(definition.voice_id)
        synthesis_started = time.perf_counter()
        raw = self.provider.synthesize(SynthesisRequest(
            text=clean_text,
            voice_id=definition.voice_id,
            provider_voice_id=definition.provider_voice_id,
            output_path=output_path,
            speed=speed,
            volume=volume,
        ))
        timings["tts.synthesize"] = round(
            (time.perf_counter() - synthesis_started) * 1000, 3
        )
        result = SynthesisResult(
            raw.success, raw.output_path, definition.voice_id, raw.provider_id,
            raw.error, requested, selection.fallback_used, selection.reason,
            timings,
        )
        if play_audio and result.success and result.output_path is not None:
            playback_started = time.perf_counter()
            if not self.player.play(result.output_path):
                timings["tts.playback"] = round(
                    (time.perf_counter() - playback_started) * 1000, 3
                )
                timings["tts.total"] = round(
                    (time.perf_counter() - total_started) * 1000, 3
                )
                return SynthesisResult(
                    False, result.output_path, result.voice_id, result.provider_id,
                    "No se pudo reproducir el WAV.", requested,
                    selection.fallback_used, selection.reason, timings,
                )
            timings["tts.playback"] = round(
                (time.perf_counter() - playback_started) * 1000, 3
            )
        timings["tts.total"] = round(
            (time.perf_counter() - total_started) * 1000, 3
        )
        return SynthesisResult(
            result.success, result.output_path, result.voice_id, result.provider_id,
            result.error, result.requested_voice_id, result.fallback_used,
            result.selection_reason, timings,
        )

    def _is_voice_available(self, definition) -> bool:
        return bool(
            definition.enabled
            and definition.provider_id == self.provider.provider_id
            and self.provider.is_available()
            and self.provider.supports_voice(definition.provider_voice_id)
        )

    def _build_output_path(self, voice_id: str) -> Path:
        safe = re.sub(r"[^a-z0-9_-]+", "_", voice_id.casefold())
        return self.output_dir / f"{safe}_{time.time_ns()}.wav"

    @staticmethod
    def clean_console_text(text: str) -> str:
        paragraphs, current = [], []
        for raw in text.replace("\r\n", "\n").split("\n"):
            line = raw.strip()
            if not line:
                if current:
                    paragraphs.append(" ".join(current)); current = []
                continue
            if line.startswith(("INFO:", "DEBUG:", "WARNING:", "ERROR:")):
                continue
            if set(line) <= {"=", "-", "_", "*"}:
                continue
            current.append(line)
        if current:
            paragraphs.append(" ".join(current))
        return re.sub(r"[ \t]+", " ", "\n\n".join(paragraphs)).strip()
