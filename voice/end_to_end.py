"""Turno de voz local: micrófono -> STT -> Atlas -> estilo -> TTS."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from time import perf_counter

from conversation.response_pipeline import DaxterResponsePipeline
from voice.models import AssistantIdentity, SynthesisResult
from voice.service import VoiceService


@dataclass(frozen=True, slots=True)
class VoiceTurnResult:
    transcript: str
    response: str
    continue_running: bool
    synthesis: SynthesisResult | None
    timings_ms: dict[str, float] = field(default_factory=dict)


class ManualVoiceSession:
    def __init__(self, *, atlas, recorder, stt, voice_service, response_pipeline=None, work_dir="runtime/voice/input") -> None:
        self.atlas = atlas
        self.recorder = recorder
        self.stt = stt
        self.voice_service = voice_service
        self.response_pipeline = response_pipeline or DaxterResponsePipeline()
        self.work_dir = Path(work_dir)
        self.previous_styled_text = ""

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
        transcript, stt_timings = self.stt.transcribe(source, language_hint="es")
        ai_started = perf_counter()
        captured = StringIO()
        with redirect_stdout(captured):
            running = self.atlas.process(transcript.text)
        ai_ms = (perf_counter() - ai_started) * 1000
        base_text = VoiceService.clean_console_text(captured.getvalue())
        timings = {"recording": round(recording_ms, 3), **stt_timings, "atlas": round(ai_ms, 3)}
        if not base_text:
            timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
            return VoiceTurnResult(transcript.text, "", running, None, timings)
        style_started = perf_counter()
        styled = self.response_pipeline.adapt(
            base_text,
            channel="pc_voice",
            request_text=transcript.text,
            user=self.atlas.get_user(),
            previous_styled_text=self.previous_styled_text,
        )
        timings["personality"] = round((perf_counter() - style_started) * 1000, 3)
        self.previous_styled_text = styled.styled_text
        tts_started = perf_counter()
        synthesis = self.voice_service.speak(
            styled.styled_text,
            identity=AssistantIdentity.DAXTER,
            emotion=styled.emotion,
            intensity=styled.intensity,
        )
        timings["tts_and_playback"] = round((perf_counter() - tts_started) * 1000, 3)
        timings["total"] = round((perf_counter() - total_started) * 1000 + recording_ms, 3)
        return VoiceTurnResult(transcript.text, styled.styled_text, running, synthesis, timings)

    def cancel(self) -> None:
        self.recorder.stop()
        self.voice_service.stop_current_audio()
        self.voice_service.clear_queue()

    def close(self) -> None:
        self.cancel()
        self.recorder.close()
        self.voice_service.close()
