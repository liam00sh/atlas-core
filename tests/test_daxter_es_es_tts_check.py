from argparse import Namespace
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import wave

import pytest

from tools.chatterbox_es_es_runtime import (
    REQUIRED_MODEL_FILES,
    load_es_es_model,
    resolve_es_es_model_dir,
)
from tools import check_daxter_es_es_tts as check
from tools import run_voice_e2e_guided as guided


def _complete(path: Path) -> Path:
    path.mkdir(parents=True)
    for name in REQUIRED_MODEL_FILES:
        (path / name).write_bytes(b"local")
    return path


def _wav(path: Path) -> Path:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(24000)
        audio.writeframes(b"\x00\x00" * 100)
    return path


def test_resolves_incomplete_download_to_comparison_runtime(tmp_path):
    requested = tmp_path / "models" / "ResembleAI" / "Chatterbox-Multilingual-es-es"
    requested.mkdir(parents=True)
    (requested / "t3_es_es.safetensors").write_bytes(b"regional")
    runtime = _complete(tmp_path / "models" / "runtime" / "chatterbox-es-es")

    route = resolve_es_es_model_dir(requested)

    assert route.effective == runtime.resolve()
    assert "ve.pt" in route.missing_requested
    assert route.ready is True


def test_missing_runtime_files_are_reported_without_download(tmp_path):
    requested = tmp_path / "model"
    requested.mkdir()
    route = resolve_es_es_model_dir(requested)
    assert route.effective == requested.resolve()
    assert set(route.missing_effective) == set(REQUIRED_MODEL_FILES)


def test_shared_loader_imports_official_module_and_uses_effective_runtime(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "chatterbox" / "src").mkdir(parents=True)
    runtime = _complete(tmp_path / "model")
    called = {}

    class FakeTTS:
        @classmethod
        def from_local(cls, path, device, **kwargs):
            called.update(path=Path(path), device=device, kwargs=kwargs)
            return SimpleNamespace(t3=SimpleNamespace(inference=lambda *a, **k: None))

    package = ModuleType("chatterbox")
    package.__path__ = []
    module = ModuleType("chatterbox.tts")
    module.ChatterboxTTS = FakeTTS
    monkeypatch.setitem(sys.modules, "chatterbox", package)
    monkeypatch.setitem(sys.modules, "chatterbox.tts", module)

    model, route = load_es_es_model(source=source, model_dir=runtime, device="cpu")

    assert route.effective == runtime.resolve()
    assert called["path"] == runtime.resolve()
    assert called["kwargs"] == {
        "t3_filename": "t3_es_es.safetensors", "s3gen_filename": "s3gen_v3.pt"
    }
    assert model is not None


def test_shared_loader_exposes_import_and_load_errors(tmp_path, monkeypatch):
    source = tmp_path / "source"; (source / "chatterbox" / "src").mkdir(parents=True)
    runtime = _complete(tmp_path / "model")
    package = ModuleType("chatterbox"); package.__path__ = []
    monkeypatch.setitem(sys.modules, "chatterbox", package)
    monkeypatch.delitem(sys.modules, "chatterbox.tts", raising=False)
    with pytest.raises(ModuleNotFoundError):
        load_es_es_model(source=source, model_dir=runtime, device="cpu")

    module = ModuleType("chatterbox.tts")
    module.ChatterboxTTS = SimpleNamespace(
        from_local=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("checkpoint incompatible"))
    )
    monkeypatch.setitem(sys.modules, "chatterbox.tts", module)
    with pytest.raises(RuntimeError, match="checkpoint incompatible"):
        load_es_es_model(source=source, model_dir=runtime, device="cpu")


def test_input_validation_reports_missing_source_model_and_reference(tmp_path):
    python = tmp_path / "python.exe"; python.write_bytes(b"exe")
    args = Namespace(tts_python=python, tts_source=tmp_path / "missing-source",
                     tts_model_dir=tmp_path / "missing-model",
                     tts_reference=tmp_path / "missing-reference.wav")
    errors = check.validate_inputs(args)
    assert any("cargador es-ES inexistente" in error for error in errors)
    assert any("modelo incompleto" in error for error in errors)
    assert any("referencia inexistente" in error for error in errors)


def test_independent_check_synthesizes_exact_phrase_and_requires_completed_playback(tmp_path, monkeypatch):
    python = tmp_path / "python.exe"; python.write_bytes(b"exe")
    source = tmp_path / "source"
    (source / "chatterbox" / "src" / "chatterbox").mkdir(parents=True)
    (source / "chatterbox" / "src" / "chatterbox" / "tts.py").write_text("", encoding="utf-8")
    model = _complete(tmp_path / "model")
    reference = _wav(tmp_path / "reference.wav")
    output = tmp_path / "check.wav"
    seen = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            self.profile = {"version": "1.0.0"}
            self.last_worker_diagnostics = {"module": "official/tts.py", "offline": True}

        def synthesize(self, request):
            seen["text"] = request.text
            output.write_bytes(b"RIFFfake")
            return SimpleNamespace(success=True, output_path=output, error=None, wav_duration_ms=800.0, cache_hit=False)

        def close(self):
            seen["closed"] = True

    player = SimpleNamespace(
        play=lambda path: seen.setdefault("played", path) is path,
        last_playback_completed=True,
    )
    monkeypatch.setattr(check, "ChatterboxDaxterProvider", FakeProvider)
    args = Namespace(tts_python=python, tts_source=source, tts_model_dir=model,
                     tts_reference=reference, output=output, no_play=False)

    report = check.run_check(args, player=player)

    assert report["success"] is True
    assert seen["text"] == "Hola, soy Daxter."
    assert seen["played"] == output and seen["closed"] is True


def test_check_tts_mode_does_not_construct_full_e2e(monkeypatch, tmp_path):
    paths = [tmp_path / name for name in ("python.exe", "source", "model", "reference.wav")]
    monkeypatch.setattr(check, "run_check", lambda args: {"success": True, "mode": "tts-only"})
    monkeypatch.setattr(sys, "argv", [
        "run_voice_e2e_guided.py", "--check-tts",
        "--tts-python", str(paths[0]), "--tts-source", str(paths[1]),
        "--tts-model-dir", str(paths[2]), "--tts-reference", str(paths[3]),
    ])
    assert guided.main() == 0


def test_e2e_preflight_aborts_when_tts_is_not_ready():
    checks = {name: {"ready": True} for name in ("microphone", "stt", "atlas", "audio_output", "tts")}
    checks["tts"]["ready"] = False
    assert guided.preflight_has_fatal_failure(checks) is True
