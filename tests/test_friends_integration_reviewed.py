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
    Alex = r.upsert_person("Alex")
    persona_ejemplo_06 = r.upsert_person("Zoe Vento Pérez")
    d = r.propose_or_apply_level_change(
        owner_person_id=Alex.person_id,
        target_person_id=persona_ejemplo_06.person_id,
        proposed_level=FriendshipLevel.FRIEND,
        confidence=0.72,
        source="conversation",
    )
    assert d.action == "ask"
    relation = r.confirm_pending_relationship_change(
        owner_person_id=Alex.person_id,
        target_person_id=persona_ejemplo_06.person_id,
        accept=True,
    )
    assert relation.friendship_level == FriendshipLevel.FRIEND

def test_home_presence_required():
    r = repo()
    grant = r.grant_permission(
        grantor_profile_id="Carla",
        target_person_id="ana",
        permission="home.light.Carla_room",
        scope="light.Carla_room",
        grantor_permissions={"home.light.Carla_room"},
        delegable_permissions={"home.light.Carla_room"},
        friendship_level=FriendshipLevel.CLOSE_FRIEND,
        target_is_home=True,
        is_admin_permission=False,
        grantor_is_admin=False,
    )
    assert r.permission_is_effective(grant, target_is_home=True)
    assert not r.permission_is_effective(grant, target_is_home=False)

def test_profile_linking():
    r = repo()
    persona_ejemplo_06 = r.upsert_person("Zoe Vento Pérez")
    r.link_profile(persona_ejemplo_06.person_id, "Zoe")
    assert r.find_person("Zoe Vento Pérez").profile_id == "Zoe"

def test_core_integration():
    root = Path(__file__).resolve().parents[1]
    text = (root/"core"/"atlas.py").read_text(encoding="utf-8")
    assert "AtlasFriendsMixin" in text
    assert "self._init_friends()" in text
