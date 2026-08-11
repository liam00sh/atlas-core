import json

from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter
from voice.style import VoiceIntensity, VoiceStyleSelector


def _files(tmp_path):
    catalog = tmp_path / "catalog.json"
    profile = tmp_path / "profile.json"
    emotions = []
    for emotion, supported, fallback in (("neutral", ["baja", "media", "alta"], "neutral"), ("risa", ["media"], "neutral")):
        emotions.append({
            "id": emotion, "preferred_energy": "media", "supported_intensities": supported,
            "fallback_emotion": fallback, "reference_audio_strategy": "winner",
            "exaggeration": {"baja": 0.45, "media": 0.55, "alta": 0.65},
            "cfg_weight": 0.35, "temperature": 0.8, "repetition_penalty": 2.0, "min_p": 0.05, "top_p": 1.0,
        })
    catalog.write_text(json.dumps({"emotions": emotions}), encoding="utf-8")
    profile.write_text(json.dumps({"language_id": "es", "reference_file": "winner.wav"}), encoding="utf-8")
    return catalog, profile


def test_unknown_emotion_falls_back_to_neutral(tmp_path):
    catalog, _ = _files(tmp_path)
    style = VoiceStyleSelector(catalog).resolve("desconocida", "alta")
    assert style.emotion == "neutral"
    assert "fallback neutral" in style.reason


def test_unsupported_intensity_uses_nearest_and_selector_is_provider_free(tmp_path):
    catalog, _ = _files(tmp_path)
    style = VoiceStyleSelector(catalog).resolve("risa", VoiceIntensity.HIGH)
    assert style.intensity == VoiceIntensity.MEDIUM
    assert not hasattr(style, "cfg_weight")


def test_chatterbox_adapter_maps_style_and_reference_fallback(tmp_path):
    catalog, profile = _files(tmp_path)
    style = VoiceStyleSelector(catalog).resolve("neutral", "alta")
    mapped = ChatterboxStyleAdapter(catalog, profile).to_tts_style(style, reference_available=False)
    assert mapped["exaggeration"] == 0.65
    assert mapped["language_id"] == "es"
    assert "fallback" in mapped["reason"]


def test_only_accepted_normalizations_are_applied(tmp_path):
    catalog, profile = _files(tmp_path)
    adapter = ChatterboxStyleAdapter(catalog, profile)
    result = adapter.normalize_text("Jak usa Atlas, Daxter, Home Assistant y Telegram el 9 de agosto de 2026.")
    assert result.startswith("Yak usa Atlas, Daxter, Home Assistant y Telegram")
    assert "nueve de agosto" in result
