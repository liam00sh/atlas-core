import os

from tools.build_daxter_emotion_lab import emotion_cases, force_offline_model_loading, player_html


def _catalog():
    names = (
        "neutral", "sonriente", "picaro", "sorprendido", "pensativo", "emocionado", "asustado",
        "enfadado", "curioso", "confiado", "risa", "cansado", "sonoliento", "determinado", "travieso",
    )
    return {"emotions": [{"id": name} for name in names]}


def test_emotion_lab_is_manageable_and_covers_all_emotions():
    cases = emotion_cases(_catalog())
    assert len(cases) == 38
    assert {case["emotion"] for case in cases} == {item["id"] for item in _catalog()["emotions"]}


def test_each_emotion_compares_winner_and_experimental_reference():
    cases = emotion_cases(_catalog())
    for emotion in {case["emotion"] for case in cases}:
        variants = {case["reference_variant"] for case in cases if case["emotion"] == emotion and case["intensity"] == "media"}
        assert variants == {"winner_diverse", "emotion_experimental"}


def test_blind_player_hides_reference_strategy():
    rendered = player_html([{"blind_code": "EM001", "emotion": "neutral", "intensity": "media", "audio_file": "blind_audio/EM001.wav"}])
    assert "winner_diverse" not in rendered
    assert "emotion_experimental" not in rendered


def test_model_loading_is_forced_offline(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "false")
    force_offline_model_loading()
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
