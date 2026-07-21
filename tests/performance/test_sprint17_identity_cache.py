"""Pruebas de seguridad e invalidación de la caché del Sprint 17."""

import json

from identity.identity_storage import IdentityStorage
from identity.person import Person


def test_repeated_identity_load_uses_cache_and_returns_independent_objects(tmp_path, monkeypatch):
    storage = IdentityStorage(tmp_path)
    storage.save_people([Person(name="Liam")])
    calls = {"count": 0}
    original = storage._load_json_list

    def counted(path):
        calls["count"] += 1
        return original(path)

    monkeypatch.setattr(storage, "_load_json_list", counted)
    first = storage.load_people()
    second = storage.load_people()
    first[0].name = "Cambio no guardado"

    assert calls["count"] == 1
    assert second[0].name == "Liam"
    assert storage.load_people()[0].name == "Liam"
    assert len(storage._entity_cache) <= 3


def test_save_invalidates_identity_cache(tmp_path):
    storage = IdentityStorage(tmp_path)
    storage.save_people([Person(name="Liam")])
    storage.load_people()
    assert storage.people_file in storage._entity_cache

    storage.save_people([Person(name="Saray")])

    assert storage.people_file not in storage._entity_cache
    assert storage.load_people()[0].name == "Saray"


def test_external_json_change_invalidates_by_file_signature(tmp_path):
    storage = IdentityStorage(tmp_path)
    storage.save_people([Person(name="Liam")])
    storage.load_people()
    payload = json.loads(storage.people_file.read_text(encoding="utf-8"))
    payload[0]["name"] = "Nombre externo más largo"
    storage.people_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )

    assert storage.load_people()[0].name == "Nombre externo más largo"


def test_cache_is_scoped_to_storage_instance(tmp_path):
    first = IdentityStorage(tmp_path / "first")
    second = IdentityStorage(tmp_path / "second")
    first.save_people([Person(name="Liam")])
    second.save_people([Person(name="Saray")])

    assert first.load_people()[0].name == "Liam"
    assert second.load_people()[0].name == "Saray"
    assert first._entity_cache is not second._entity_cache
