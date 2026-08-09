from __future__ import annotations

from pathlib import Path

import pytest

from telegram_interface.outbound import TelegramOutboundError, TelegramOutboundMediaService
from tools.capability import Capability
from tools.context import ToolContext
from tools.telegram_media import TelegramSendMediaTool


class Client:
    def __init__(self): self.calls = []
    def __getattr__(self, name):
        if name.startswith("send_"):
            return lambda **kwargs: self.calls.append((name, kwargs)) or {}
        raise AttributeError(name)


def jpeg_bytes():
    return b"\xff\xd8\xff" + b"safe-image" + b"\xff\xd9"


def service(tmp_path, client=None, audit=None):
    root = tmp_path / "outbox"
    root.mkdir(exist_ok=True)
    return TelegramOutboundMediaService(
        client=client or Client(),
        account_resolver=lambda user: {"state": "linked", "chat_id": "private-chat"} if user == "User-A" else None,
        allowed_roots={"outbox": root, "generated": root / "generated"},
        max_bytes={"photo": 1024, "voice": 1024, "audio": 1024, "document": 1024},
        audit=audit,
    )


def test_sends_only_to_callers_linked_chat_from_relative_allowed_path(tmp_path):
    client = Client()
    media = service(tmp_path, client)
    target = tmp_path / "outbox" / "photo.jpg"
    target.write_bytes(jpeg_bytes())
    result = media.send(requested_by="User-A", media_type="photo", root_name="outbox", relative_path="photo.jpg")
    assert result.mime_type == "image/jpeg"
    assert client.calls[0][0] == "send_photo"
    assert client.calls[0][1]["chat_id"] == "private-chat"


@pytest.mark.parametrize("path", ["../secret.jpg", "C:/private/secret.jpg", "/private/secret.jpg"])
def test_rejects_traversal_and_absolute_paths_before_upload(tmp_path, path):
    media = service(tmp_path)
    with pytest.raises(TelegramOutboundError) as raised:
        media.send(requested_by="User-A", media_type="photo", root_name="outbox", relative_path=path)
    assert raised.value.code == "path_denied"


def test_personal_data_requires_confirmation_and_unlinked_user_is_denied(tmp_path):
    media = service(tmp_path)
    target = tmp_path / "outbox" / "photo.jpg"
    target.write_bytes(jpeg_bytes())
    with pytest.raises(TelegramOutboundError) as raised:
        media.send(requested_by="User-A", media_type="photo", root_name="outbox", relative_path="photo.jpg", contains_personal_data=True)
    assert raised.value.code == "confirmation_required"
    with pytest.raises(TelegramOutboundError) as raised:
        media.send(requested_by="User-B", media_type="photo", root_name="outbox", relative_path="photo.jpg")
    assert raised.value.code == "recipient_not_linked"


def test_false_extension_and_executable_signature_are_rejected(tmp_path):
    client = Client()
    media = service(tmp_path, client)
    target = tmp_path / "outbox" / "photo.jpg"
    target.write_bytes(b"MZ" + b"not-an-image")
    with pytest.raises(TelegramOutboundError) as raised:
        media.send(requested_by="User-A", media_type="photo", root_name="outbox", relative_path="photo.jpg")
    assert raised.value.code == "media_executable"
    assert client.calls == []


def test_generated_file_is_cleaned_only_when_explicitly_requested(tmp_path):
    media = service(tmp_path)
    generated = tmp_path / "outbox" / "generated"
    generated.mkdir()
    target = generated / "photo.jpg"
    target.write_bytes(jpeg_bytes())
    media.send(requested_by="User-A", media_type="photo", root_name="generated", relative_path="photo.jpg", delete_after_send=True)
    assert not target.exists()


def test_symlink_cannot_escape_allowed_root(tmp_path):
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(jpeg_bytes())
    link = tmp_path / "outbox" / "linked.jpg"
    link.parent.mkdir(exist_ok=True)
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("El entorno no permite crear enlaces simbólicos.")
    with pytest.raises(TelegramOutboundError) as raised:
        service(tmp_path).send(
            requested_by="User-A", media_type="photo", root_name="outbox", relative_path="linked.jpg"
        )
    assert raised.value.code == "path_denied"


def test_tool_requires_matching_permission_and_never_accepts_chat_id(tmp_path):
    client = Client()
    media = service(tmp_path, client)
    target = tmp_path / "outbox" / "photo.jpg"
    target.write_bytes(jpeg_bytes())
    tool = TelegramSendMediaTool("photo", media)
    denied = tool.execute(Capability("telegram.send_photo"), {"root": "outbox", "relative_path": "photo.jpg"}, ToolContext("User-A"))
    assert denied.error == "permission_denied"
    allowed = tool.execute(
        Capability("telegram.send_photo"),
        {"root": "outbox", "relative_path": "photo.jpg", "chat_id": "attacker-chat"},
        ToolContext("User-A", permissions={"telegram.send_photo"}),
    )
    assert allowed.success
    assert client.calls[0][1]["chat_id"] == "private-chat"
