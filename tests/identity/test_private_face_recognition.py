from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest

from identity.face_recognition import (
    FaceAccessContext,
    FaceIdentityStore,
    FacePolicyError,
    PrivateFaceRecognitionService,
)


class Provider:
    def __init__(self):
        self.values = {}
    def is_available(self): return True
    def model_version(self): return "local-model-v1"
    def embeddings(self, path): return self.values.get(str(path), [])
    def similarity(self, left, right): return 1.0 - abs(float(left[0]) - float(right[0]))


def access(*permissions, guest=False, chat_type="private", admin=True):
    return FaceAccessContext("Admin-A", frozenset(permissions), chat_type, True, guest, admin)


def test_enrollment_stores_only_minimal_biometric_schema_and_no_images(tmp_path):
    provider = Provider()
    provider.values = {"one": [[0.1, 0.2]], "two": [[0.11, 0.19]]}
    store = FaceIdentityStore(tmp_path / "private" / "faces.json")
    events = []
    service = PrivateFaceRecognitionService(store, provider, audit=lambda action, result: events.append((action, result)))
    service.enroll(
        "person-001", ["one", "two"], access("face.enroll"),
        consent_at=datetime(2025, 1, 1, tzinfo=UTC), reinforced_confirmation=True,
    )
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    record = payload["identities"]["person-001"]
    assert set(record) == {
        "person_id", "embeddings", "model_version", "consent_at", "created_at",
        "updated_at", "active", "revoked_at",
    }
    assert "one" not in store.path.read_text(encoding="utf-8")
    assert events == [("face.enroll", "ok")]


def test_recognition_is_conservative_and_never_identifies_low_confidence(tmp_path):
    provider = Provider()
    provider.values = {"one": [[0.1]], "two": [[0.1]], "high": [[0.11]], "low": [[0.25]], "none": [[0.8]]}
    service = PrivateFaceRecognitionService(FaceIdentityStore(tmp_path / "faces.json"), provider)
    service.enroll("person-001", ["one", "two"], access("face.enroll"), consent_at=datetime(2025, 1, 1, tzinfo=UTC), reinforced_confirmation=True)
    assert service.recognize("high", access("face.recognize"))[0].status == "recognized"
    low = service.recognize("low", access("face.recognize"))[0]
    assert low.status == "possible_match"
    assert low.person_id is None
    assert service.recognize("none", access("face.recognize"))[0].status == "unrecognized"


@pytest.mark.parametrize(
    "context",
    [access("face.recognize", guest=True), access("face.recognize", chat_type="group"), access()],
)
def test_guests_groups_and_missing_permission_are_denied(tmp_path, context):
    service = PrivateFaceRecognitionService(FaceIdentityStore(tmp_path / "faces.json"), Provider())
    with pytest.raises(FacePolicyError):
        service.recognize("photo", context)


def test_revoke_requires_reinforced_confirmation_and_removes_embeddings(tmp_path):
    provider = Provider()
    provider.values = {"one": [[0.1]], "two": [[0.1]]}
    store = FaceIdentityStore(tmp_path / "faces.json")
    service = PrivateFaceRecognitionService(store, provider)
    service.enroll("person-001", ["one", "two"], access("face.enroll"), consent_at=datetime(2025, 1, 1, tzinfo=UTC), reinforced_confirmation=True)
    with pytest.raises(FacePolicyError):
        service.revoke("person-001", access("face.revoke"), reinforced_confirmation=False)
    assert service.revoke("person-001", access("face.revoke"), reinforced_confirmation=True)
    assert store.get("person-001") is None
