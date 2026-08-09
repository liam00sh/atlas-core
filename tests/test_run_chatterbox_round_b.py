import wave

from tools.run_chatterbox_round_b import stable_seed, wav_metrics


def test_stable_seed_is_repeatable_and_candidate_specific():
    assert stable_seed(20260809, "B1", "original", "01") == stable_seed(20260809, "B1", "original", "01")
    assert stable_seed(20260809, "B1", "original", "01") != stable_seed(20260809, "B2", "original", "01")


def test_wav_metrics_flags_excess_duration(tmp_path):
    path = tmp_path / "long.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x10" * (16000 * 8))
    metrics = wav_metrics(path, "Hola")
    assert metrics["audio_seconds"] == 8.0
    assert "duration_excess" in metrics["automatic_flags"]
