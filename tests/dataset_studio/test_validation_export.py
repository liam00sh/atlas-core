from __future__ import annotations

import json
from pathlib import Path

from atlas_dataset_studio.dataset import DatasetProject
from atlas_dataset_studio.exporters import export_dataset
from atlas_dataset_studio.validators import validate_dataset


def test_validation_hashes_manifest_and_exports(dataset_fixture, tmp_path):
    project = DatasetProject.open(dataset_fixture)
    try:
        result = validate_dataset(dataset_fixture, project.samples)
        assert result.valid and result.checked_files == 3
        project.update_current(review_status="accepted", personality_usable=True, tts_usable=True)
        output = tmp_path / "exports"; result = export_dataset(dataset_fixture, project.samples, output)
        assert result.valid
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["file_count"] == 3 and "audio_root" not in json.dumps(manifest)
        assert len((output / "tts_dataset.jsonl").read_text(encoding="utf-8").splitlines()) == 1
        assert len((output / "personality_dataset.jsonl").read_text(encoding="utf-8").splitlines()) == 1
        assert (output / "DATASET_VALIDATION_REPORT.md").is_file()
    finally: project.close()


def test_missing_audio_duplicate_and_bad_hash(dataset_fixture):
    project = DatasetProject.open(dataset_fixture, read_only=True)
    try:
        project.samples[0].sha256 = "bad"
        project.samples[1].relative_path = project.samples[0].relative_path
        project.samples[2].relative_path = "missing.wav"
        result = validate_dataset(dataset_fixture, project.samples)
        joined = "\n".join(result.errors)
        assert "hash SHA-256 incorrecto" in joined
        assert "ruta duplicada" in joined
        assert "audio ausente" in joined
    finally: project.close()


def test_corrupt_wav(dataset_fixture):
    (dataset_fixture.audio_root / "sample_1.wav").write_bytes(b"not-a-wave")
    project = DatasetProject.open(dataset_fixture, read_only=True)
    try: assert any("WAV corrupto" in error for error in validate_dataset(dataset_fixture, project.samples).errors)
    finally: project.close()
