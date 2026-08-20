from pathlib import Path
from types import SimpleNamespace
import wave
import pytest

from tools.run_voice_e2e_guided import (
    case_payload, collect_human_evaluation, combine_wavs, load_or_initialize,
    limited_phrases, phrases, played_audio_sources, preflight,
    preserve_played_audio, replay_audio, successful_playback, TurnAudioError,
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


def _turn(*, spoken="Respuesta.", success=True, playback=True, paths=(), error=None):
    synthesis = SynthesisResult(
        success, paths[-1] if paths else None, "daxter_official", "fake", error,
        playback_completed=playback, segment_output_paths=tuple(paths),
    )
    return SimpleNamespace(spoken_response=spoken, synthesis=synthesis)


def test_exact_sources_empty_regression_is_rejected_with_contract_error():
    with pytest.raises(TurnAudioError, match="perdió segment_output_paths"):
        played_audio_sources(_turn(paths=()))


@pytest.mark.parametrize(
    ("turn", "message"),
    [
        (_turn(spoken=""), "texto hablado está vacío"),
        (_turn(success=False, playback=False, error="worker failed"), "TTS falló: worker failed"),
        (_turn(playback=False, error="speaker failed"), "Playback no completado"),
    ],
)
def test_invalid_tts_turns_never_reach_human_review(turn, message):
    with pytest.raises(TurnAudioError, match=message):
        played_audio_sources(turn)


def test_disappeared_segment_is_reported(tmp_path):
    missing = tmp_path / "deleted.wav"
    with pytest.raises(TurnAudioError, match="ya no existe"):
        played_audio_sources(_turn(paths=(missing,)))


def test_one_and_multiple_played_segments_are_preserved(tmp_path):
    first, second = tmp_path / "first.wav", tmp_path / "second.wav"
    _wav(first, 100); _wav(second, 150)
    one = preserve_played_audio(played_audio_sources(_turn(paths=(first,))), tmp_path / "one.wav")
    assert one.read_bytes() == first.read_bytes()
    multiple = preserve_played_audio(
        played_audio_sources(_turn(paths=(first, second))), tmp_path / "multiple.wav"
    )
    with wave.open(str(multiple), "rb") as audio:
        assert audio.getnframes() == 250


def test_smoke_scope_selects_only_real_case_one():
    selected = limited_phrases(known_name="persona de prueba", max_items=1)
    assert selected == ("Hola Daxter, ¿qué tal estás?",)


def test_automated_one_case_smoke_preserves_exact_played_audio(tmp_path):
    played = tmp_path / "played.wav"
    _wav(played, 240)
    turn = _turn(spoken="Estoy bien y lista para ayudarte.", paths=(played,))

    sources = played_audio_sources(turn)
    preserved = preserve_played_audio(sources, tmp_path / "case_001.wav")

    assert sources == (played,)
    assert preserved.read_bytes() == played.read_bytes()


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


def test_preflight_reports_exact_tts_runtime_and_root_exception():
    provider = SimpleNamespace(
        worker_command=["private-python.exe", "worker.py"], source_path=Path("source-es-es"),
        reference_path=Path("reference.wav"),
        health=lambda: {"model_requested": "download-model", "model_effective": "runtime-model"},
    )
    voice_service = SimpleNamespace(
        provider=provider,
        player=SimpleNamespace(is_available=lambda: True),
        speak=lambda *args, **kwargs: SimpleNamespace(
            success=False, playback_completed=False, error="FileNotFoundError: ve.pt"
        ),
    )
    atlas = SimpleNamespace(
        process=lambda text: text,
        stage_e_environment=SimpleNamespace(adapter=SimpleNamespace(health=lambda: {"available": True})),
        _queue=lambda: SimpleNamespace(list_pending=lambda user: []), get_user=lambda: "test",
    )
    recorder = SimpleNamespace(is_available=lambda: True, selected_device=lambda: "microphone")
    stt_provider = SimpleNamespace(health=lambda: {"available": True})

    checks = preflight(atlas, recorder, stt_provider, voice_service)

    assert checks["tts"]["status"] == "ERROR"
    assert checks["tts"]["error"] == "FileNotFoundError: ve.pt"
    assert checks["tts"]["python"] == "private-python.exe"
    assert checks["tts"]["model_effective"] == "runtime-model"
