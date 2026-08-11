"""Turno de voz local: micrófono -> STT -> Atlas -> estilo -> TTS."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

from ai.context.context_manager import AIContextManager
from core.request_timing import RequestTiming, bind_request_timing, reset_request_timing
from conversation.response_pipeline import DaxterResponsePipeline
from voice.models import AssistantIdentity, SynthesisResult
from voice.service import VoiceService
from voice.stt import STTError
from voice.stt_policy import STTDecisionKind, STTInputPolicy, STTIntentContext
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


class ManualVoiceSession:
    def __init__(self, *, atlas, recorder, stt, voice_service, response_pipeline=None, work_dir="runtime/voice/input") -> None:
        self.atlas = atlas
        self.recorder = recorder
        self.stt = stt
        self.voice_service = voice_service
        self.response_pipeline = response_pipeline or DaxterResponsePipeline()
        self.work_dir = Path(work_dir)
        self.previous_styled_text = ""
        self.session_id = f"pc_voice:{uuid4().hex}"
        self.stt_policy = STTInputPolicy()
        self._ai_context = AIContextManager(
            max_messages=getattr(atlas, "ai_context_max_messages", 10)
        )

    def capture_turn(self, *, input_func=input) -> VoiceTurnResult:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        source = self.work_dir / "manual_capture.wav"
        started = perf_counter()
        try:
            self.recorder.record_on_enter(source, input_func=input_func)
            recording_ms = (perf_counter() - started) * 1000
            return self.process_recording(source, recording_ms=recording_ms)
        finally:
            source.unlink(missing_ok=True)

    def process_recording(self, source: str | Path, *, recording_ms: float = 0.0) -> VoiceTurnResult:
        total_started = perf_counter()
        timings = {"recording": round(recording_ms, 3)}
        try:
            transcript, stt_timings = self.stt.transcribe(source, language_hint="es")
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
        normalized = ContextualTranscriptNormalizer.normalize(transcript)
        decision = self.stt_policy.evaluate(
            normalized,
            STTIntentContext(has_temporary_memory=bool(self.previous_styled_text)),
        )
        timings["stt.policy"] = round((perf_counter() - policy_started) * 1000, 3)
        if decision.kind is not STTDecisionKind.PROCESS:
            response = decision.response or "No he podido confirmar la transcripcion."
            synthesis = self._safe_speak(response, emotion="neutral", intensity="baja")
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            return VoiceTurnResult(normalized.text, response, response, True, synthesis, timings, decision.kind.value)

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
        speech_started = perf_counter()
        spoken_response = SpeechTextNormalizer.normalize(styled.styled_text, max_sentences=3)
        timings["speech.normalize"] = round((perf_counter() - speech_started) * 1000, 3)
        tts_started = perf_counter()
        tts_stages: dict[str, float] = {}
        synthesis = self._safe_speak(
            spoken_response,
            emotion=styled.emotion,
            intensity=styled.intensity,
            timings=tts_stages,
        )
        timings.update({f"tts.{key}": value for key, value in tts_stages.items()})
        timings["tts_and_playback"] = round((perf_counter() - tts_started) * 1000, 3)
        timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
        error = None if synthesis is None or synthesis.success else synthesis.error
        return VoiceTurnResult(decision.text, styled.styled_text, spoken_response, running, synthesis, timings, error)

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
            return self.voice_service.speak(
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
