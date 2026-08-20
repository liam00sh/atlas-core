"""Turno de voz local: micrófono -> STT -> Atlas -> estilo -> TTS."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Callable
from uuid import uuid4

from ai.context.context_manager import AIContextManager
from core.request_timing import RequestTiming, bind_request_timing, reset_request_timing
from conversation.response_pipeline import DaxterResponsePipeline
from voice.conversation_state import (
    PendingTranscriptConfirmation,
    VoiceConfirmationState,
    VoiceConversationMemory,
)
from voice.models import AssistantIdentity, SynthesisResult
from voice.service import VoiceService
from voice.stt import STTError
from voice.stt_policy import STTDecision, STTDecisionKind, STTInputPolicy, STTIntentContext
from voice.text_normalizer import ContextualTranscriptNormalizer, SpeechTextNormalizer


@dataclass(frozen=True, slots=True)
class VoiceTurnResult:
    transcript: str
    response: str
    spoken_response: str
    continue_running: bool
    synthesis: SynthesisResult | None
    timings_ms: dict[str, float] = field(default_factory=dict)
    recoverable_error: str | None = None
    trace: dict[str, object] = field(default_factory=dict)


class ManualVoiceSession:
    def __init__(
        self, *, atlas, recorder, stt, voice_service, response_pipeline=None,
        work_dir="runtime/voice/input",
        trace_callback: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self.atlas = atlas
        self.recorder = recorder
        self.stt = stt
        self.voice_service = voice_service
        self.response_pipeline = response_pipeline or DaxterResponsePipeline()
        self.work_dir = Path(work_dir)
        self.previous_styled_text = ""
        self.memory = VoiceConversationMemory()
        self.pending_transcript: PendingTranscriptConfirmation | None = None
        self.last_stt_corrections: tuple[dict[str, str], ...] = ()
        self.session_id = f"pc_voice:{uuid4().hex}"
        self.stt_policy = STTInputPolicy()
        self.trace_callback = trace_callback
        self._ai_context = AIContextManager(
            max_messages=getattr(atlas, "ai_context_max_messages", 10)
        )

    def capture_turn(self, *, input_func=input) -> VoiceTurnResult:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        source = self.work_dir / "manual_capture.wav"
        started = perf_counter()
        try:
            self._emit_trace("recording", recording_path=str(source))
            self.recorder.record_on_enter(source, input_func=input_func)
            recording_ms = (perf_counter() - started) * 1000
            result = self.process_recording(source, recording_ms=recording_ms)
            result.trace.setdefault("recording_path", str(source))
            return result
        finally:
            source.unlink(missing_ok=True)

    def process_recording(self, source: str | Path, *, recording_ms: float = 0.0) -> VoiceTurnResult:
        total_started = perf_counter()
        timings = {"recording": round(recording_ms, 3)}
        try:
            pending_confirmation = self._has_pending_confirmation() or self.pending_transcript is not None
            context_hint = "confirmation" if pending_confirmation else "general"
            transcript, stt_timings = self._transcribe(
                source,
                language_hint="es",
                context_hint=context_hint,
            )
        except STTError as exc:
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            message = self._stt_error_message(exc.code)
            return VoiceTurnResult("", message, message, True, None, timings, exc.code)
        except (OSError, RuntimeError, ValueError) as exc:
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            message = "No he podido transcribir este turno. Puedes intentarlo otra vez."
            return VoiceTurnResult("", message, message, True, None, timings, type(exc).__name__)

        timings.update(stt_timings)
        policy_started = perf_counter()
        raw_transcript = transcript.text
        normalized = ContextualTranscriptNormalizer.normalize(
            transcript,
            pending_confirmation=pending_confirmation,
            known_names=self._known_names(),
        )
        self.last_stt_corrections = (
            ({"raw": raw_transcript, "normalized": normalized.text},)
            if raw_transcript != normalized.text else ()
        )
        previous_raw_transcript = self.memory.last_raw_transcript
        previous_normalized_transcript = self.memory.last_normalized_transcript
        self.memory.last_user_utterance = raw_transcript
        self.memory.last_raw_transcript = raw_transcript
        self.memory.last_normalized_transcript = normalized.text
        self._emit_trace(
            "transcription",
            raw_transcript=raw_transcript,
            normalized_transcript=normalized.text,
        )
        if self.pending_transcript is not None:
            decision, immediate_response = self._resolve_transcript_confirmation(normalized.text)
            if immediate_response is not None:
                synthesis = self._safe_speak(immediate_response, emotion="neutral", intensity="baja")
                timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
                return VoiceTurnResult(
                    normalized.text, immediate_response, immediate_response, True, synthesis,
                    timings, None, self._trace(confirmation_state=VoiceConfirmationState.NONE),
                )
        else:
            decision = self.stt_policy.evaluate(
                normalized,
                STTIntentContext(
                    has_temporary_memory=bool(self.previous_styled_text),
                    pending_confirmation=self._has_pending_confirmation(),
                ),
            )
        timings["stt.policy"] = round((perf_counter() - policy_started) * 1000, 3)
        if decision.kind is not STTDecisionKind.PROCESS:
            response = decision.response or "No he podido confirmar la transcripcion."
            state = VoiceConfirmationState.NONE
            if decision.kind is STTDecisionKind.CONFIRM:
                self.pending_transcript = PendingTranscriptConfirmation(raw_transcript, decision.text)
                state = VoiceConfirmationState.TRANSCRIPT_CONFIRMATION
            synthesis = self._safe_speak(response, emotion="neutral", intensity="baja")
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            return VoiceTurnResult(
                normalized.text, response, response, True, synthesis, timings,
                decision.kind.value, self._trace(confirmation_state=state),
            )

        repeated = self._repeat_response(
            decision.text,
            previous_raw=previous_raw_transcript,
            previous_normalized=previous_normalized_transcript,
        )
        if repeated is not None:
            synthesis = self._safe_speak(repeated, emotion="neutral", intensity="baja")
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            return VoiceTurnResult(
                decision.text, repeated, repeated, True, synthesis, timings,
                trace=self._trace(confirmation_state=self._confirmation_state()),
            )

        ai_started = perf_counter()
        atlas_timing = RequestTiming()
        timing_token = bind_request_timing(atlas_timing)
        captured = StringIO()
        try:
            with redirect_stdout(captured):
                running = self._process_with_pc_context(decision.text)
        except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
            timings["atlas"] = round((perf_counter() - ai_started) * 1000, 3)
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            message = "Este turno ha fallado antes de completar la respuesta. La sesi\u00f3n sigue disponible."
            return VoiceTurnResult(decision.text, message, message, True, None, timings, type(exc).__name__)
        finally:
            reset_request_timing(timing_token)
        ai_ms = (perf_counter() - ai_started) * 1000
        base_text = VoiceService.clean_console_text(captured.getvalue())
        self._emit_trace("atlas", atlas_response=base_text)
        self.memory.last_base_response = base_text
        timings["atlas"] = round(ai_ms, 3)
        timings.update({f"atlas.{key}": value for key, value in atlas_timing.snapshot().items()})
        if not base_text:
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            return VoiceTurnResult(decision.text, "", "", running, None, timings)
        style_started = perf_counter()
        styled = self.response_pipeline.adapt(
            base_text,
            channel="pc_voice",
            request_text=decision.text,
            user=self.atlas.get_user(),
            previous_styled_text=self.previous_styled_text,
        )
        timings["personality"] = round((perf_counter() - style_started) * 1000, 3)
        self.previous_styled_text = styled.styled_text
        self.memory.last_styled_response = styled.styled_text
        speech_started = perf_counter()
        spoken_response = SpeechTextNormalizer.normalize(
            styled.styled_text,
            max_sentences=2 if self._asks_for_brief(decision.text) else None,
            max_chars=360 if self._asks_for_brief(decision.text) else None,
        )
        self.memory.last_spoken_response = spoken_response
        segment_planner = getattr(self.voice_service, "segments_for_text", None)
        planned_segments = (
            segment_planner(spoken_response)
            if callable(segment_planner) else ((spoken_response,) if spoken_response else ())
        )
        self._emit_trace(
            "speech",
            styled_response=styled.styled_text,
            spoken_text=spoken_response,
            number_of_tts_segments_expected=len(planned_segments),
        )
        timings["speech.normalize"] = round((perf_counter() - speech_started) * 1000, 3)
        tts_started = perf_counter()
        tts_stages: dict[str, float] = {}
        synthesis = self._safe_speak(
            spoken_response,
            emotion=styled.emotion,
            intensity=styled.intensity,
            timings=tts_stages,
        )
        self._emit_trace(
            "tts",
            number_of_tts_segments_generated=len(getattr(synthesis, "segment_output_paths", ())) if synthesis else 0,
            generated_wav_paths=[str(path) for path in getattr(synthesis, "segment_output_paths", ())] if synthesis else [],
            playback_paths=[str(path) for path in getattr(synthesis, "segment_output_paths", ())] if synthesis else [],
            playback_completed=getattr(synthesis, "playback_completed", None) if synthesis else None,
            error=getattr(synthesis, "error", None) if synthesis else "empty spoken text",
        )
        timings.update({f"tts.{key}": value for key, value in tts_stages.items()})
        timings["tts_and_playback"] = round((perf_counter() - tts_started) * 1000, 3)
        timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
        timings["total_without_recording"] = round((perf_counter() - total_started) * 1000, 3)
        error = None if synthesis is None or synthesis.success else synthesis.error
        trace = {
            "atlas_base_response": base_text,
            "visible_text": styled.styled_text,
            "spoken_text": spoken_response,
            "emotion": styled.emotion,
            "intensity": styled.intensity,
            "chars_sent_to_tts": len(spoken_response),
            "chars_synthesized": getattr(synthesis, "chars_synthesized", 0) if synthesis else 0,
            "synthesized_samples": getattr(synthesis, "synthesized_samples", 0) if synthesis else 0,
            "wav_duration_ms": getattr(synthesis, "wav_duration_ms", 0.0) if synthesis else 0.0,
            "playback_duration_ms": getattr(synthesis, "playback_duration_ms", 0.0) if synthesis else 0.0,
            "playback_completed": getattr(synthesis, "playback_completed", None) if synthesis else None,
            "playback_interrupted": getattr(synthesis, "playback_interrupted", False) if synthesis else False,
            "number_of_tts_segments_expected": len(planned_segments),
            "segments": list(getattr(synthesis, "segment_texts", ())) if synthesis else [],
            "segment_chars": list(getattr(synthesis, "segment_chars", ())) if synthesis else [],
            "segment_wav_durations_ms": list(getattr(synthesis, "segment_wav_durations_ms", ())) if synthesis else [],
            "segment_output_paths": [str(path) for path in getattr(synthesis, "segment_output_paths", ())] if synthesis else [],
            "confirmation_state": self._confirmation_state().value,
            "conversation_memory": self.memory.public_trace(),
            "stt": {
                "raw": raw_transcript,
                "normalized": normalized.text,
                "corrections": list(self.last_stt_corrections),
                "confidence": str(normalized.confidence),
                "context": "confirmation" if pending_confirmation else "general",
            },
        }
        return VoiceTurnResult(
            decision.text, styled.styled_text, spoken_response, running,
            synthesis, timings, error, trace,
        )

    def _emit_trace(self, stage: str, **payload: object) -> None:
        if self.trace_callback is not None:
            self.trace_callback(stage, payload)

    def _has_pending_confirmation(self) -> bool:
        confirmations = getattr(self.atlas, "confirmations", None)
        checker = getattr(confirmations, "has_pending_confirmation", None)
        return bool(checker()) if callable(checker) else False

    def _confirmation_state(self) -> VoiceConfirmationState:
        if self.pending_transcript is not None:
            return VoiceConfirmationState.TRANSCRIPT_CONFIRMATION
        if self._has_pending_confirmation():
            manager = getattr(self.atlas, "confirmations", None)
            getter = getattr(manager, "get_confirmation", None)
            pending = getter() if callable(getter) else None
            if isinstance(pending, dict) and pending.get("confirmation_state") == VoiceConfirmationState.DANGEROUS_ACTION_CONFIRMATION.value:
                return VoiceConfirmationState.DANGEROUS_ACTION_CONFIRMATION
            return VoiceConfirmationState.ACTION_CONFIRMATION
        return VoiceConfirmationState.NONE

    def _trace(self, *, confirmation_state: VoiceConfirmationState) -> dict[str, object]:
        return {
            "confirmation_state": confirmation_state.value,
            "conversation_memory": self.memory.public_trace(),
            "stt_corrections": list(self.last_stt_corrections),
            "stt": {
                "raw": self.memory.last_raw_transcript,
                "normalized": self.memory.last_normalized_transcript,
                "corrections": list(self.last_stt_corrections),
                "context": "confirmation" if confirmation_state is not VoiceConfirmationState.NONE else "general",
            },
        }

    def _known_names(self) -> tuple[str, ...]:
        manager = getattr(self.atlas, "people_manager", None)
        getter = getattr(manager, "get_people", None)
        if not callable(getter):
            return ()
        try:
            return tuple(
                str(person.name).strip()
                for person in getter()
                if str(getattr(person, "name", "")).strip()
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return ()

    def _resolve_transcript_confirmation(self, answer: str) -> tuple[STTDecision, str | None]:
        assert self.pending_transcript is not None
        plain = ContextualTranscriptNormalizer._plain(answer)
        accepted = {"si", "correcto", "eso es", "vale", "confirmo", "adelante"}
        rejected = {"no", "incorrecto", "no era eso", "cancela", "cancelar", "dejalo"}
        if plain in accepted:
            stored = self.pending_transcript.normalized_transcript
            self.pending_transcript = None
            return STTDecision(STTDecisionKind.PROCESS, stored), None
        if plain in rejected:
            self.pending_transcript = None
            return STTDecision(STTDecisionKind.REPEAT, answer), "Entendido. He descartado esa transcripción. Repítelo cuando quieras."
        stored = self.pending_transcript.normalized_transcript
        return (
            STTDecision(STTDecisionKind.CONFIRM, stored),
            f"Sigo esperando una confirmación. ¿He entendido «{stored}»?",
        )

    def _repeat_response(
        self,
        text: str,
        *,
        previous_raw: str = "",
        previous_normalized: str = "",
    ) -> str | None:
        plain = ContextualTranscriptNormalizer._plain(text)
        if plain in {"repite", "repite tu respuesta", "que has dicho"}:
            return self.memory.last_spoken_response or "Todavía no tengo una respuesta anterior que repetir."
        if plain in {"repite lo que he dicho", "que he dicho", "que has entendido"}:
            if not previous_raw:
                return "Todavía no tengo una entrada anterior que repetir."
            return (
                f"He oído: {previous_raw}. "
                f"He interpretado: {previous_normalized}."
            )
        return None

    @staticmethod
    def _asks_for_brief(text: str) -> bool:
        plain = ContextualTranscriptNormalizer._plain(text)
        return any(token in plain for token in ("breve", "resumen", "resumelo", "en corto"))

    def _transcribe(self, source, *, language_hint: str, context_hint: str):
        import inspect

        parameters = inspect.signature(self.stt.transcribe).parameters
        if "context_hint" in parameters:
            return self.stt.transcribe(
                source,
                language_hint=language_hint,
                context_hint=context_hint,
            )
        return self.stt.transcribe(source, language_hint=language_hint)

    def _process_with_pc_context(self, text: str) -> bool:
        previous_context = getattr(self.atlas, "channel_request_context", None)
        previous_session = getattr(self.atlas, "session_id", None)
        ai_contexts = getattr(self.atlas, "ai_contexts", None)
        user_key = self.atlas.get_user().strip().casefold()
        previous_ai_context = ai_contexts.get(user_key) if isinstance(ai_contexts, dict) else None
        try:
            self.atlas.channel_request_context = SimpleNamespace(
                channel="pc_voice",
                atlas_user_id=self.atlas.get_user(),
                session_id=self.session_id,
            )
            self.atlas.session_id = self.session_id
            if isinstance(ai_contexts, dict):
                ai_contexts[user_key] = self._ai_context
            return bool(self.atlas.process(text))
        finally:
            if isinstance(ai_contexts, dict):
                self._ai_context = ai_contexts.get(user_key, self._ai_context)
                if previous_ai_context is None:
                    ai_contexts.pop(user_key, None)
                else:
                    ai_contexts[user_key] = previous_ai_context
            self.atlas.channel_request_context = previous_context
            self.atlas.session_id = previous_session

    def _safe_speak(self, text: str, *, emotion: str, intensity: str, timings=None) -> SynthesisResult | None:
        if not text:
            return None
        try:
            speak = (
                self.voice_service.speak_segmented
                if hasattr(self.voice_service, "speak_segmented")
                else self.voice_service.speak
            )
            return speak(
                text,
                identity=AssistantIdentity.DAXTER,
                emotion=emotion,
                intensity=intensity,
                timings=timings,
            )
        except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
            return SynthesisResult(
                False, None, "daxter_official", "text",
                f"{type(exc).__name__}: salida textual conservada",
                requested_voice_id="daxter_official",
                selection_reason="fallback textual tras error recuperable",
            )

    @staticmethod
    def _stt_error_message(code: str) -> str:
        safe_messages = {
            "audio_empty": "No he detectado voz en este turno. Pulsa Enter y vuelve a intentarlo.",
            "stt_timeout": "La transcripci\u00f3n ha tardado demasiado. La sesi\u00f3n sigue abierta para otro intento.",
            "audio_convert_timeout": "La transcripci\u00f3n ha tardado demasiado. La sesi\u00f3n sigue abierta para otro intento.",
        }
        return safe_messages.get(
            code,
            "No he podido transcribir este audio. La sesi\u00f3n sigue abierta para otro intento.",
        )

    def cancel(self) -> None:
        self.recorder.stop()
        self.voice_service.stop_current_audio()
        self.voice_service.clear_queue()

    def close(self) -> None:
        self.cancel()
        self.recorder.close()
        self.voice_service.close()
