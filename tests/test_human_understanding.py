from core.atlas_understanding import _plain, UnderstandingStorage
from pathlib import Path


def test_plain_normalizes_accents():
    assert _plain("¿Qué mensaje te aparece?") == "que mensaje te aparece"


def test_storage_roundtrip(tmp_path: Path):
    storage = UnderstandingStorage(tmp_path / "u.json")
    storage.update(lambda data: data.setdefault("users", {}).update({"REDACTED_f73137d930c3": {"ok": True}}))
    assert storage.snapshot()["users"]["REDACTED_f73137d930c3"]["ok"] is True
