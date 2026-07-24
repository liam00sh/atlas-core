from pathlib import Path
import tempfile
import pytest
from core.atlas_friends import FriendsRepository, FriendshipLevel

def repo():
    temp = tempfile.TemporaryDirectory()
    repository = FriendsRepository(Path(temp.name) / "friends.json")
    repository._tempdir = temp
    return repository

def test_known_is_below_friendship_levels():
    assert FriendshipLevel.KNOWN == 0
    assert FriendshipLevel.KNOWN_FRIEND == 1
    assert FriendshipLevel.BEST_FRIEND == 4

def test_high_confidence_applies_automatically():
    r = repo()
    REDACTED_f73137d930c3 = r.upsert_person("REDACTED_2c7b6821719d")
    REDACTED_3a6d64c24cf8 = r.upsert_person("REDACTED_53b1fb446230 Vento Pérez")
    result = r.propose_or_apply_level_change(
        owner_person_id=REDACTED_f73137d930c3.person_id,
        target_person_id=REDACTED_3a6d64c24cf8.person_id,
        proposed_level=FriendshipLevel.CLOSE_FRIEND,
        confidence=0.91,
        source="conversation",
    )
    assert result.action == "applied"

def test_medium_confidence_asks_user():
    r = repo()
    REDACTED_f73137d930c3 = r.upsert_person("REDACTED_2c7b6821719d")
    REDACTED_3a6d64c24cf8 = r.upsert_person("REDACTED_53b1fb446230 Vento Pérez")
    result = r.propose_or_apply_level_change(
        owner_person_id=REDACTED_f73137d930c3.person_id,
        target_person_id=REDACTED_3a6d64c24cf8.person_id,
        proposed_level=FriendshipLevel.FRIEND,
        confidence=0.70,
        source="conversation",
    )
    assert result.action == "ask"

def test_friend_permission_requires_level_3_or_4():
    r = repo()
    with pytest.raises(PermissionError):
        r.grant_permission(
            grantor_profile_id="REDACTED_1552db05a755",
            target_person_id="ana",
            permission="home.light.REDACTED_1552db05a755_room",
            scope="light.REDACTED_1552db05a755_room",
            grantor_permissions={"home.light.REDACTED_1552db05a755_room"},
            delegable_permissions={"home.light.REDACTED_1552db05a755_room"},
            friendship_level=FriendshipLevel.FRIEND,
            target_is_home=True,
            is_admin_permission=False,
            grantor_is_admin=False,
        )

def test_friend_permission_requires_home_presence():
    r = repo()
    with pytest.raises(PermissionError):
        r.grant_permission(
            grantor_profile_id="REDACTED_1552db05a755",
            target_person_id="ana",
            permission="home.light.REDACTED_1552db05a755_room",
            scope="light.REDACTED_1552db05a755_room",
            grantor_permissions={"home.light.REDACTED_1552db05a755_room"},
            delegable_permissions={"home.light.REDACTED_1552db05a755_room"},
            friendship_level=FriendshipLevel.CLOSE_FRIEND,
            target_is_home=False,
            is_admin_permission=False,
            grantor_is_admin=False,
        )

def test_admin_permissions_are_never_delegated():
    r = repo()
    with pytest.raises(PermissionError):
        r.grant_permission(
            grantor_profile_id="REDACTED_f73137d930c3",
            target_person_id="ana",
            permission="atlas.create_user",
            scope=None,
            grantor_permissions={"atlas.create_user"},
            delegable_permissions={"atlas.create_user"},
            friendship_level=FriendshipLevel.BEST_FRIEND,
            target_is_home=True,
            is_admin_permission=True,
            grantor_is_admin=True,
        )
