from pathlib import Path
import tempfile
from core.atlas_friends import FriendsRepository, FriendshipLevel

def repo():
    temp = tempfile.TemporaryDirectory()
    r = FriendsRepository(Path(temp.name) / "friends.json")
    r._tempdir = temp
    return r

def test_pending_confirmation():
    r = repo()
    REDACTED_f73137d930c3 = r.upsert_person("REDACTED_2c7b6821719d")
    REDACTED_3a6d64c24cf8 = r.upsert_person("REDACTED_53b1fb446230 Vento Pérez")
    d = r.propose_or_apply_level_change(
        owner_person_id=REDACTED_f73137d930c3.person_id,
        target_person_id=REDACTED_3a6d64c24cf8.person_id,
        proposed_level=FriendshipLevel.FRIEND,
        confidence=0.72,
        source="conversation",
    )
    assert d.action == "ask"
    relation = r.confirm_pending_relationship_change(
        owner_person_id=REDACTED_f73137d930c3.person_id,
        target_person_id=REDACTED_3a6d64c24cf8.person_id,
        accept=True,
    )
    assert relation.friendship_level == FriendshipLevel.FRIEND

def test_home_presence_required():
    r = repo()
    grant = r.grant_permission(
        grantor_profile_id="REDACTED_1552db05a755",
        target_person_id="ana",
        permission="home.light.REDACTED_1552db05a755_room",
        scope="light.REDACTED_1552db05a755_room",
        grantor_permissions={"home.light.REDACTED_1552db05a755_room"},
        delegable_permissions={"home.light.REDACTED_1552db05a755_room"},
        friendship_level=FriendshipLevel.CLOSE_FRIEND,
        target_is_home=True,
        is_admin_permission=False,
        grantor_is_admin=False,
    )
    assert r.permission_is_effective(grant, target_is_home=True)
    assert not r.permission_is_effective(grant, target_is_home=False)

def test_profile_linking():
    r = repo()
    REDACTED_3a6d64c24cf8 = r.upsert_person("REDACTED_53b1fb446230 Vento Pérez")
    r.link_profile(REDACTED_3a6d64c24cf8.person_id, "REDACTED_3a6d64c24cf8")
    assert r.find_person("REDACTED_53b1fb446230 Vento Pérez").profile_id == "REDACTED_3a6d64c24cf8"

def test_core_integration():
    root = Path(__file__).resolve().parents[1]
    text = (root/"core"/"atlas.py").read_text(encoding="utf-8")
    assert "AtlasFriendsMixin" in text
    assert "self._init_friends()" in text
