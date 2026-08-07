from __future__ import annotations

import csv
import hashlib
import wave
from pathlib import Path

import pytest

from atlas_dataset_studio.models import ProjectConfig


@pytest.fixture
def dataset_fixture(tmp_path: Path) -> ProjectConfig:
    audio = tmp_path / "audio"; audio.mkdir()
    rows = []
    for index, text in enumerate(("Hola Jak", "¿Vamos a ganar la carrera?", "¡Era una broma!"), 1):
        path = audio / f"sample_{index}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(bytes((index, 0)) * 2400)
        rows.append({
            "sample_id": f"daxter_{index:04d}", "audio_file": path.name,
            "relative_path": path.name, "text": text, "normalized_text": text,
            "source_game": "jak2" if index < 3 else "jak3", "duration_seconds": ".1",
            "sample_rate": "24000", "channels": "1", "sample_width_bits": "16",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "emotion": "neutral",
            "emotion_confidence": "baja", "intention": "indeterminada", "energy": "media",
            "personality_usable": "False", "personality_tags": "", "personality_reason": "",
            "tts_usable": "True", "review_status": "pending_review", "review_notes": "",
            "needs_human_review": "True", "legacy_field": f"keep-{index}",
        })
    metadata = tmp_path / "metadata.csv"
    with metadata.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    return ProjectConfig("Daxter test", "daxter_es", "voice/personality", audio, metadata, tmp_path / "workspace")
