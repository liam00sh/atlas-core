from __future__ import annotations

from datetime import UTC, datetime
from time import sleep

from core.atlas_executive import AtlasExecutiveMixin
from telegram_interface.gateway import TelegramGateway
from telegram_interface.models import GatewayResponse, TelegramMessage, TelegramUser
from telegram_interface.polling import TelegramPoller


def _message(*, text: str, media_type: str | None = None) -> TelegramMessage:
    return TelegramMessage(
        update_id=1,
        message_id=10,
        user=TelegramUser(telegram_user_id="1", chat_id="100"),
        text=text,
        timestamp=datetime.now(UTC),
        media_type=media_type,
    )


def test_photo_caption_is_not_sent_to_ai_as_visual_fact() -> None:
    response = TelegramGateway._handle_media_message(
        _message(text="Mira, este es Funcio", media_type="photo")
    )
    assert "He recibido la foto" in response.text
    assert "todavía no puedo ver la imagen" in response.text
    assert "tu gato de" not in response.text
    assert "Lidia" not in response.text


def test_executive_summarizes_long_explanations() -> None:
    text = (
        "Mira, llevo toda la mañana con el móvil y no sé qué pasa. "
        "La cámara antes funcionaba bien. Ahora quiero hacer una foto, "
        "me sale un mensaje y no puedo continuar. Necesito que me ayudes "
        "a averiguar qué ocurre sin borrar mis fotos. "
        "También he reiniciado el teléfono y sigue igual."
    )
    summary = AtlasExecutiveMixin._summarize_long_message(text)
    assert "Necesito" in summary or "quiero" in summary
    assert len(summary) <= 700


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def get_webhook_info(self):
        return {"url": ""}

    def get_updates(self, *, offset: int, timeout: int):
        return []

    def send_message(self, *, chat_id: str, text: str, parse_mode=None):
        self.sent.append(text)
        return {}


class _FakeGateway:
    def handle(self, message):
        sleep(0.06)
        return GatewayResponse("respuesta final")


class _FakeStorage:
    def get_offset(self):
        return 0

    def set_offset(self, _offset):
        return None


def test_progress_is_delivered_before_final_response() -> None:
    client = _FakeClient()
    poller = TelegramPoller(
        client=client,
        gateway=_FakeGateway(),
        storage=_FakeStorage(),
        progress_delay_seconds=0.01,
        progress_message_factory=lambda _message: "procesando",
    )
    response = poller._handle_with_ordered_progress(_message(text="consulta compleja"))
    poller._send_chunks("100", response.text, response.parse_mode)
    poller.stop()
    assert client.sent == ["procesando", "respuesta final"]
