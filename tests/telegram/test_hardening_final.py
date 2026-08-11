from pathlib import Path

from telegram_interface.client import TelegramClientError
from telegram_interface.models import TelegramMessage
from telegram_interface.polling import TelegramPoller

from tests.telegram.conftest import link_user, make_message


class MediaClient:
    def __init__(self, metadata=None):
        self.metadata = metadata or {"file_path": "documents/report.bin", "file_size": 8}

    def get_file(self, *, file_id):
        return dict(self.metadata)

    def download_file(self, *, file_path, destination, max_bytes):
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"content")
        return target

    def get_webhook_info(self):
        return {"url": ""}

    def get_updates(self, **_kwargs):
        return []

    def send_message(self, **_kwargs):
        return {}


class PassiveGateway:
    linker = None

    def handle(self, _message):
        raise AssertionError("No debe procesarse en esta prueba")


def media_message(**changes):
    values = dict(
        update_id=1,
        message_id=2,
        user=make_message("x").user,
        text="",
        media_type="document",
        file_id="safe-file-id",
        file_name="engaño.exe",
        mime_type="text/plain",
        file_size=8,
    )
    values.update(changes)
    return TelegramMessage(**values)


def build_poller(tmp_path, client=None, **kwargs):
    return TelegramPoller(
        client=client or MediaClient(),
        gateway=PassiveGateway(),
        storage=kwargs.pop("storage"),
        media_root=tmp_path / "media",
        media_max_bytes=32,
        media_ttl_hours=1,
        **kwargs,
    )


def test_media_uses_verified_mime_not_sender_extension(tmp_path, storage):
    poller = build_poller(tmp_path, storage=storage)
    prepared = poller._prepare_media(media_message())
    try:
        assert prepared.media_status == "quarantined"
        assert Path(prepared.local_path).suffix == ".txt"
        assert not Path(prepared.local_path).name.endswith(".exe")
    finally:
        poller._cleanup_message_media(prepared)
        poller.stop()
    assert not Path(prepared.local_path).exists()


def test_document_without_mime_and_oversized_metadata_are_rejected(tmp_path, storage):
    poller = build_poller(tmp_path, storage=storage)
    try:
        assert poller._prepare_media(media_message(mime_type=None)).media_status == "rejected_type"
        oversized = MediaClient({"file_path": "documents/a.txt", "file_size": 100})
        poller.client = oversized
        assert poller._prepare_media(media_message()).media_status == "rejected_too_large"
    finally:
        poller.stop()


def test_invalid_remote_path_is_never_downloaded(tmp_path, storage):
    client = MediaClient({"file_path": "../secret.txt", "file_size": 8})
    poller = build_poller(tmp_path, client=client, storage=storage)
    try:
        assert poller._prepare_media(media_message()).media_status == "metadata_missing"
    finally:
        poller.stop()


def test_rate_limit_retry_after_is_honoured(storage, tmp_path):
    delays = []

    class RateLimited(MediaClient):
        calls = 0

        def get_updates(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TelegramClientError(
                    "rate", retryable=True, kind="rate_limit", retry_after=7
                )
            return []

    poller = TelegramPoller(
        client=RateLimited(), gateway=PassiveGateway(), storage=storage,
        sleeper=delays.append, media_root=tmp_path / "media",
    )
    poller.run(max_cycles=2)
    assert delays == [7]


def test_linked_help_uses_core_with_bound_identity(gateway, linker):
    link_user(linker, atlas_user="Vega")
    response = gateway.handle(make_message("/help"))
    assert response.text == "Vega:ayuda"


def test_media_analyzer_receives_atlas_identity_not_telegram_id(gateway):
    seen = []
    gateway.core.analyze_media = lambda **kwargs: seen.append(kwargs) or "analizado"
    message = media_message(local_path="C:/temp/safe.txt", media_status="quarantined")
    response = gateway._handle_media_message(message, atlas_user_id="Vega")
    assert response.text == "analizado"
    assert seen[0]["user_id"] == "Vega"
