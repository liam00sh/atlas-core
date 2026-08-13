"""Servicio común con B1, fallback local, caché y reproducción cancelable."""

from __future__ import annotations

from pathlib import Path
import re
import time

from voice.catalog.voices import VOICE_CATALOG
from voice.config import COCO_PREFERRED_VOICE, DAXTER_PREFERRED_VOICE, VOICE_OUTPUT_DIR
from voice.models import AssistantIdentity, SynthesisRequest, SynthesisResult
from voice.playback_queue import PlaybackQueue
from voice.player import WavePlayer
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.providers.kokoro_provider import KokoroProvider
from voice.resolver.voice_resolver import VoiceResolver
from voice.segmentation import split_for_speech


class VoiceService:
    def __init__(
        self,
        *,
        provider=None,
        providers=None,
        player=None,
        output_dir=None,
        playback_queue=None,
    ) -> None:
        if provider is not None:
            resolved_providers = [provider]
        elif providers is not None:
            resolved_providers = list(providers)
        else:
            resolved_providers = [ChatterboxDaxterProvider(), KokoroProvider()]
        self.providers = {item.provider_id: item for item in resolved_providers}
        self.provider = resolved_providers[0] if resolved_providers else None
        self.player = player or WavePlayer()
        self.output_dir = Path(output_dir or VOICE_OUTPUT_DIR)
        self.playback_queue = playback_queue or PlaybackQueue(self.player)
        self.resolver = VoiceResolver(availability_check=self._is_voice_available)

    def is_available(self) -> bool:
        return any(provider.is_available() for provider in self.providers.values()) and self.player.is_available()

    def preferred_voice(self, identity, preferences=None) -> str:
        if preferences is not None:
            return preferences.preferred_voice_for(identity)
        return COCO_PREFERRED_VOICE if identity is AssistantIdentity.COCO else DAXTER_PREFERRED_VOICE

    def speak(
        self,
        text: str,
        *,
        identity,
        requested_voice_id=None,
        preferences=None,
        speed=1.0,
        volume=1.0,
        emotion="neutral",
        intensity="media",
        play_audio=True,
        queue_audio=False,
        timings=None,
    ) -> SynthesisResult:
        timings = timings if isinstance(timings, dict) else {}
        resolve_started = time.perf_counter()
        identity = AssistantIdentity(identity)
        clean_text = self.clean_console_text(text)
        requested = requested_voice_id or self.preferred_voice(identity, preferences)
        timings["resolve"] = round((time.perf_counter() - resolve_started) * 1000, 3)
        if not clean_text:
            return SynthesisResult(False, None, requested, "none", "No hay texto reproducible.", requested_voice_id=requested)

        fallback_enabled = preferences.fallback_enabled if preferences else True
        failures: list[str] = []
        for candidate_id in self.resolver.candidates(
            identity=identity,
            requested_voice_id=requested,
            fallback_enabled=fallback_enabled,
        ):
            definition = VOICE_CATALOG.get(candidate_id)
            if definition is None or definition.identity is not identity:
                continue
            provider = self.providers.get(definition.provider_id)
            if provider is None or not self._is_voice_available(definition):
                continue
            output_path = self._build_output_path(definition.voice_id)
            synthesis_started = time.perf_counter()
            raw = provider.synthesize(SynthesisRequest(
                text=clean_text,
                voice_id=definition.voice_id,
                provider_voice_id=definition.provider_voice_id,
                output_path=output_path,
                speed=speed,
                volume=volume,
                emotion=emotion,
                intensity=intensity,
                voice_profile_id=definition.provider_voice_id,
                profile_version=str(definition.metadata.get("profile_version", "1.0.0")),
            ))
            timings["synthesis"] = round((time.perf_counter() - synthesis_started) * 1000, 3)
            if not raw.success:
                failures.append(f"{definition.voice_id}: {raw.error or 'fallo de síntesis'}")
                continue
            result = SynthesisResult(
                success=True,
                output_path=raw.output_path,
                voice_id=definition.voice_id,
                provider_id=raw.provider_id,
                error=None,
                requested_voice_id=requested,
                fallback_used=definition.voice_id != requested,
                selection_reason=("voz solicitada disponible" if definition.voice_id == requested else "fallback TTS local"),
                cache_hit=raw.cache_hit,
                latency_ms=raw.latency_ms,
                emotion=raw.emotion or emotion,
                intensity=raw.intensity or intensity,
                chars_sent_to_tts=len(clean_text),
                chars_synthesized=raw.chars_synthesized,
                synthesized_samples=raw.synthesized_samples,
                wav_duration_ms=raw.wav_duration_ms,
            )
            timings["spoken_chars"] = result.chars_sent_to_tts
            timings["chars_synthesized"] = result.chars_synthesized
            timings["synthesized_samples"] = result.synthesized_samples
            timings["wav_duration_ms"] = result.wav_duration_ms
            if play_audio and result.output_path is not None:
                playback_started = time.perf_counter()
                playback_ticket = None
                if queue_audio:
                    playback_ticket = self.playback_queue.enqueue(result.output_path)
                elif not self.player.play(result.output_path):
                    elapsed_ms = round((time.perf_counter() - playback_started) * 1000, 3)
                    timings["playback"] = elapsed_ms
                    timings["playback_duration_ms"] = elapsed_ms
                    timings["playback_completed"] = False
                    timings["playback_interrupted"] = False
                    return SynthesisResult(
                        success=False,
                        output_path=result.output_path,
                        voice_id=result.voice_id,
                        provider_id=result.provider_id,
                        error="No se pudo reproducir el WAV.",
                        requested_voice_id=requested,
                        fallback_used=result.fallback_used,
                        selection_reason=result.selection_reason,
                        cache_hit=result.cache_hit,
                        latency_ms=result.latency_ms,
                        emotion=result.emotion,
                        intensity=result.intensity,
                        chars_sent_to_tts=result.chars_sent_to_tts,
                        chars_synthesized=result.chars_synthesized,
                        synthesized_samples=result.synthesized_samples,
                        wav_duration_ms=result.wav_duration_ms,
                        playback_duration_ms=elapsed_ms,
                        playback_completed=False,
                    )
                elapsed_ms = round((time.perf_counter() - playback_started) * 1000, 3)
                timings["playback"] = elapsed_ms
                if queue_audio:
                    playback_duration_ms = 0.0
                    playback_completed = None
                    playback_interrupted = False
                else:
                    playback_duration_ms = float(
                        getattr(self.player, "last_playback_duration_ms", elapsed_ms)
                    )
                    playback_completed = bool(
                        getattr(self.player, "last_playback_completed", True)
                    )
                    playback_interrupted = bool(
                        getattr(self.player, "last_playback_interrupted", False)
                    )
                timings["playback_duration_ms"] = playback_duration_ms
                timings["playback_completed"] = playback_completed
                timings["playback_interrupted"] = playback_interrupted
                result = SynthesisResult(
                    success=result.success,
                    output_path=result.output_path,
                    voice_id=result.voice_id,
                    provider_id=result.provider_id,
                    error=result.error,
                    requested_voice_id=result.requested_voice_id,
                    fallback_used=result.fallback_used,
                    selection_reason=result.selection_reason,
                    cache_hit=result.cache_hit,
                    latency_ms=result.latency_ms,
                    emotion=result.emotion,
                    intensity=result.intensity,
                    chars_sent_to_tts=result.chars_sent_to_tts,
                    chars_synthesized=result.chars_synthesized,
                    synthesized_samples=result.synthesized_samples,
                    wav_duration_ms=result.wav_duration_ms,
                    playback_duration_ms=playback_duration_ms,
                    playback_completed=playback_completed,
                    playback_interrupted=playback_interrupted,
                    playback_ticket=playback_ticket,
                )
            return result
        detail = "; ".join(failures) if failures else "ninguna voz local compatible está disponible"
        return SynthesisResult(
            False, None, requested, "text", f"{detail}; usar salida textual",
            requested_voice_id=requested, selection_reason="fallback textual",
            emotion=emotion, intensity=intensity,
        )

    def speak_segmented(self, text: str, **kwargs) -> SynthesisResult:
        """Sintetiza N+1 mientras la cola reproduce N, conservando el orden."""
        segments = split_for_speech(self.clean_console_text(text))
        if len(segments) <= 1:
            return self.speak(text, **kwargs)
        results: list[SynthesisResult] = []
        for segment in segments:
            result = self.speak(segment, queue_audio=True, **kwargs)
            results.append(result)
            if not result.success:
                self.stop_current_audio()
                self.clear_queue()
                return result
        last = results[-1]
        tickets = [item.playback_ticket for item in results if item.playback_ticket is not None]
        timeout = max(10.0, sum(item.wav_duration_ms for item in results) / 1000.0 + 10.0)
        playback_completed = all(ticket.wait(timeout) and ticket.completed for ticket in tickets)
        playback_interrupted = any(ticket.interrupted for ticket in tickets)
        playback_duration_ms = sum(ticket.duration_ms for ticket in tickets)
        return SynthesisResult(
            success=True,
            output_path=last.output_path,
            voice_id=last.voice_id,
            provider_id=last.provider_id,
            requested_voice_id=last.requested_voice_id,
            fallback_used=any(item.fallback_used for item in results),
            selection_reason=last.selection_reason,
            cache_hit=all(item.cache_hit for item in results),
            latency_ms=sum(item.latency_ms or 0.0 for item in results),
            emotion=last.emotion,
            intensity=last.intensity,
            chars_sent_to_tts=sum(item.chars_sent_to_tts for item in results),
            chars_synthesized=sum(item.chars_synthesized for item in results),
            synthesized_samples=sum(item.synthesized_samples for item in results),
            wav_duration_ms=sum(item.wav_duration_ms for item in results),
            playback_duration_ms=playback_duration_ms,
            playback_completed=playback_completed,
            playback_interrupted=playback_interrupted,
            segment_count=len(segments),
            segment_texts=segments,
            segment_chars=tuple(len(item) for item in segments),
            segment_wav_durations_ms=tuple(item.wav_duration_ms for item in results),
        )

    def _is_voice_available(self, definition) -> bool:
        provider = self.providers.get(definition.provider_id)
        return bool(
            definition.enabled
            and provider is not None
            and provider.is_available()
            and provider.supports_voice(definition.provider_voice_id)
        )

    def _build_output_path(self, voice_id: str) -> Path:
        safe = re.sub(r"[^a-z0-9_-]+", "_", voice_id.casefold())
        return self.output_dir / f"{safe}_{time.time_ns()}.wav"

    def stop_current_audio(self) -> None:
        self.playback_queue.stop_current_audio()
        for provider in self.providers.values():
            cancel = getattr(provider, "cancel_current", None)
            if callable(cancel):
                cancel()

    def clear_queue(self) -> int:
        return self.playback_queue.clear_queue()

    def close(self) -> None:
        self.playback_queue.close()
        for provider in self.providers.values():
            close = getattr(provider, "close", None)
            if callable(close):
                close()

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
