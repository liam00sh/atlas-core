import os
from pathlib import Path

from core.user_manager import UserManager
from identity.identity_storage import IdentityStorage


ROOT = Path(__file__).resolve().parents[1]
REAL_IDENTITY_DATA = (ROOT / "examples" / "private_runtime" / "identity").resolve()
REAL_USER_DATA = (ROOT / "data" / "users").resolve()


def test_default_identity_storage_is_a_temporary_copy():
    storage = IdentityStorage()

    assert storage.data_folder == Path(
        os.environ["ATLAS_IDENTITY_DATA_DIR"]
    ).resolve()
    assert storage.data_folder != REAL_IDENTITY_DATA
    assert storage.people_file.read_bytes() == (
        REAL_IDENTITY_DATA / "people.json"
    ).read_bytes()


def test_default_identity_writes_never_touch_project_data():
    real_people_before = (REAL_IDENTITY_DATA / "people.json").read_bytes()
    storage = IdentityStorage()
    Alex = next(
        person
        for person in storage.load_people()
        if person.user_profile == "Alex"
    )

    Alex.register_encounter("2026-07-31T12:00:00")
    assert storage.update_person(Alex)

    assert storage.people_file.parent != REAL_IDENTITY_DATA
    assert (REAL_IDENTITY_DATA / "people.json").read_bytes() == real_people_before


def test_user_profile_storage_is_temporary():
    manager = UserManager()
    manager.register_profile("Invitado de prueba")

    profile_dir = manager.get_profile_data_dir("Invitado de prueba")

    assert profile_dir.is_relative_to(
        Path(os.environ["ATLAS_USER_DATA_DIR"]).resolve()
    )
    assert not profile_dir.is_relative_to(REAL_USER_DATA)
    assert (profile_dir / "internet_history.jsonl").is_file()
