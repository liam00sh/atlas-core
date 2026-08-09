import csv
import hashlib
import struct
import wave

from tools.audit_daxter_dataset import audit_wav, mark_duplicates


def _wav(path, samples, rate=16000):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def test_audit_valid_wav_and_duplicate_detection(tmp_path):
    samples = [0] * 100 + [2000, -2000] * 1000 + [0] * 100
    first = tmp_path / "a.wav"
    second = tmp_path / "b.wav"
    _wav(first, samples)
    _wav(second, samples)
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    rows = [
        {"sample_id": "a", "audio_file": "a.wav", "relative_path": "a.wav", "source_game": "jak2", "sha256": digest, "sample_rate": "16000", "channels": "1", "sample_width_bits": "16", "duration_seconds": "0.1375"},
        {"sample_id": "b", "audio_file": "b.wav", "relative_path": "b.wav", "source_game": "jak2", "sha256": digest, "sample_rate": "16000", "channels": "1", "sample_width_bits": "16", "duration_seconds": "0.1375"},
    ]
    results = [audit_wav(row, tmp_path) for row in rows]
    assert all(result.readable for result in results)
    assert all(result.metadata_sha256_match for result in results)
    mark_duplicates(results)
    assert results[0].exact_duplicate_group == results[1].exact_duplicate_group
    assert results[0].severity == "REVIEW"


def test_audit_missing_wav_is_error(tmp_path):
    row = {"sample_id": "x", "audio_file": "missing.wav", "relative_path": "missing.wav", "source_game": "jak2", "sha256": ""}
    result = audit_wav(row, tmp_path)
    assert result.severity == "ERROR"
    assert result.issues == "missing_audio"
