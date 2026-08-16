from argparse import Namespace
from pathlib import Path

import pytest

from tools.run_stt_human_battery import build_stt_config, migrate_rows, preflight_stt
from voice.stt import STTConfig, STTError, STTResult


def test_explicit_local_config_never_enables_download(tmp_path):
    args = Namespace(
        stt_model="medium", stt_model_path=tmp_path,
        device="cpu", compute_type="int8",
    )
    config = build_stt_config(args, STTConfig(allow_model_download=True))
    assert config.model == "medium"
    assert config.model_path == tmp_path.resolve()
    assert config.device == "cpu"
    assert config.compute_type == "int8"
    assert config.allow_model_download is False


def test_resume_detects_existing_wav_without_rerecording(tmp_path):
    (tmp_path / "stt_001.wav").write_bytes(b"RIFF existing recording")
    rows = [{"id": "1", "raw_transcript": "", "status": ""}]
    fields = ["id", "raw_transcript"]
    migrate_rows(rows, fields, tmp_path)
    assert rows[0]["status"] == "recorded"
    assert Path(rows[0]["audio_file"]).name == "stt_001.wav"
    assert "stt_confidence" in fields


class _Provider:
    def health(self):
        return {"available": True, "device": "cpu", "compute_type": "int8", "fallback_reason": None}


class _Service:
    def __init__(self, work_dir, result=None, error=None):
        self.work_dir = work_dir
        self.result = result
        self.error = error
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append(Path(path))
        if self.error:
            raise self.error
        return self.result, {}


def test_preflight_actually_transcribes_existing_recording(tmp_path):
    probe = tmp_path / "existing.wav"
    probe.write_bytes(b"probe")
    result = STTResult("hola")
    service = _Service(tmp_path, result=result)
    assert preflight_stt(service, _Provider(), STTConfig(), probe) is result
    assert service.calls == [probe]


def test_preflight_rejects_real_transcription_error(tmp_path):
    probe = tmp_path / "existing.wav"
    probe.write_bytes(b"probe")
    service = _Service(tmp_path, error=STTError("stt_runtime_error", "failed"))
    with pytest.raises(STTError, match="failed"):
        preflight_stt(service, _Provider(), STTConfig(), probe)
