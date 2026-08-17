from pathlib import Path
from types import SimpleNamespace
import wave
import pytest

from tools.run_voice_e2e_guided import (
    case_payload, collect_human_evaluation, combine_wavs, load_or_initialize,
    phrases, replay_audio, successful_playback,
)
from voice.models import SynthesisResult


def test_guided_e2e_keeps_confirmation_and_cancel_adjacent():
    guided_phrases = phrases(known_name="persona de prueba")
    assert len(guided_phrases) == 13
    restart = guided_phrases.index("Reinicia Telegram.")
    assert guided_phrases[restart + 1] == "Cancelar."
    assert "Saluda a persona de prueba." in guided_phrases
    assert any("acuario pequeño" in phrase for phrase in guided_phrases)


def _wav(path, frames):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * frames)


def test_guided_e2e_invalidates_schema1_and_resumes_schema2(tmp_path):
    output = tmp_path / "results.json"
    output.write_text('{"schema_version": 1, "cases": [{"index": 1}]}', encoding="utf-8")
    report = load_or_initialize(output, microphone="headset")
    assert report["schema_version"] == 2 and report["phase_status"] == "OPEN"
    assert output.with_name("results.invalidated-schema1.json").is_file()
    output.write_text('{"schema_version": 2, "cases": [{"index": 2, "rated": true}]}', encoding="utf-8")
    assert load_or_initialize(output, microphone="new")["cases"][0]["rated"] is True


def test_guided_e2e_combines_exact_played_segments(tmp_path):
    first, second, target = tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "case.wav"
    _wav(first, 100); _wav(second, 150)
    combine_wavs((first, second), target)
    with wave.open(str(target), "rb") as audio:
        assert audio.getnframes() == 250


def test_failed_turn_is_never_human_ratable():
    failed = SimpleNamespace(recoverable_error="stt_unavailable", synthesis=None)
    assert successful_playback(failed) is False
    synthesis = SynthesisResult(True, Path("answer.wav"), "daxter_official", "fake", playback_completed=True)
    result = SimpleNamespace(
        recoverable_error=None, synthesis=synthesis, trace={"stt": {"raw": "hola", "normalized": "Hola"}},
        transcript="Hola", response="Bien", spoken_response="Bien", timings_ms={},
    )
    assert successful_playback(result) is True
    payload = case_payload(1, "Hola", result, Path("private.wav"))
    assert payload["raw_transcript"] == "hola" and payload["rated"] is False
    assert payload["spoken_text"] == "Bien" and payload["audio_path"] == "private.wav"


def test_human_voice_questions_are_impossible_before_playback():
    prompts = []
    with pytest.raises(RuntimeError):
        collect_human_evaluation({"playback_completed": False}, input_func=lambda prompt: prompts.append(prompt) or "5")
    assert prompts == []
    case = {"playback_completed": True, "state_before": None}
    answers = iter(("s", "5", "4", "5", "5", "4", "5", "ok"))
    collect_human_evaluation(case, input_func=lambda prompt: prompts.append(prompt) or next(answers))
    assert case["rated"] is True and case["human_voice_naturalness"] == "5"
    assert "Naturalidad de voz" in prompts[3]


def test_repeat_audio_uses_saved_wav_without_tts():
    calls = []
    player = SimpleNamespace(play=lambda path: calls.append(path) or True)
    saved = Path("case_001.wav")
    assert replay_audio(player, saved) is True
    assert calls == [saved]
