"""Aplica la integración de notas de voz de Telegram."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"Ya aplicado: {path.relative_to(ROOT)}")
        return
    if old not in content:
        raise RuntimeError(
            f"No se encontró el bloque esperado en {path.relative_to(ROOT)}"
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    print(f"Actualizado: {path.relative_to(ROOT)}")


def main() -> int:
    client = ROOT / "telegram_interface" / "client.py"
    polling = ROOT / "telegram_interface" / "polling.py"
    runtime = ROOT / "telegram_interface" / "runtime.py"
    response_modes = ROOT / "telegram_interface" / "response_modes.py"

    replace_once(
        client,
        "from urllib.parse import urlencode\n",
        "from urllib.parse import urlencode\nimport mimetypes\nimport uuid\n",
    )

    replace_once(
        client,
        "    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> dict[str, Any]: ...\n",
        "    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> dict[str, Any]: ...\n"
        "    def send_voice(self, *, chat_id: str, voice_path: str | Path, caption: str | None = None) -> dict[str, Any]: ...\n",
    )

    send_voice = """
    def send_voice(
        self,
        *,
        chat_id: str,
        voice_path: str | Path,
        caption: str | None = None,
    ) -> dict[str, Any]:
        path = Path(voice_path)
        if not path.is_file():
            raise TelegramClientError(
                "No existe el audio que se debe enviar.",
                code="voice_file_missing",
            )

        boundary = f"----AtlasTelegram{uuid.uuid4().hex}"
        mime_type = mimetypes.guess_type(path.name)[0] or "audio/ogg"
        pieces: list[bytes] = []

        def add_field(name: str, value: str) -> None:
            pieces.extend(
                [
                    f"--{boundary}\\r\\n".encode(),
                    (
                        f'Content-Disposition: form-data; '
                        f'name="{name}"\\r\\n\\r\\n'
                    ).encode(),
                    value.encode("utf-8"),
                    b"\\r\\n",
                ]
            )

        add_field("chat_id", chat_id)
        if caption:
            add_field("caption", caption)

        pieces.extend(
            [
                f"--{boundary}\\r\\n".encode(),
                (
                    'Content-Disposition: form-data; name="voice"; '
                    f'filename="{path.name}"\\r\\n'
                ).encode(),
                f"Content-Type: {mime_type}\\r\\n\\r\\n".encode(),
                path.read_bytes(),
                b"\\r\\n",
                f"--{boundary}--\\r\\n".encode(),
            ]
        )

        request = Request(
            f"{self._base_url}/sendVoice",
            data=b"".join(pieces),
            method="POST",
            headers={
                "Content-Type": (
                    "multipart/form-data; "
                    f"boundary={boundary}"
                )
            },
        )

        try:
            with self._opener(request, timeout=90) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise TelegramClientError(
                f"Telegram rechazó la nota de voz HTTP {exc.code}.",
                code=f"telegram_http_{exc.code}",
                retryable=exc.code == 429 or exc.code >= 500,
            ) from None
        except (
            URLError,
            TimeoutError,
            socket.timeout,
            OSError,
            json.JSONDecodeError,
        ):
            raise TelegramClientError(
                "No se pudo enviar la nota de voz.",
                code="telegram_voice_unavailable",
                retryable=True,
            ) from None

        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            raise TelegramClientError(
                "Telegram devolvió un resultado inválido al enviar voz.",
                code="telegram_voice_invalid_response",
            )

        result = decoded.get("result")
        return result if isinstance(result, dict) else {}

"""
    replace_once(
        client,
        "    def get_me(self) -> dict[str, Any]:\n",
        send_voice + "    def get_me(self) -> dict[str, Any]:\n",
    )

    replace_once(
        polling,
        "from telegram_interface.models import TelegramMessage\n",
        "from telegram_interface.models import TelegramMessage\n"
        "from telegram_interface.response_modes import resolve_delivery_mode\n"
        "from telegram_interface.voice_delivery import TelegramVoiceRenderer\n",
    )

    replace_once(
        polling,
        "        wall_clock: Callable[[], float] = wall_time,\n    ) -> None:\n",
        "        wall_clock: Callable[[], float] = wall_time,\n"
        "        voice_renderer: TelegramVoiceRenderer | None = None,\n"
        "        response_mode_store=None,\n"
        "    ) -> None:\n",
    )

    replace_once(
        polling,
        "        self.wall_clock = wall_clock\n",
        "        self.wall_clock = wall_clock\n"
        "        self.voice_renderer = voice_renderer\n"
        "        self.response_mode_store = response_mode_store\n",
    )

    replace_once(
        polling,
        "                    self._send_chunks(message.user.chat_id, response.text, response.parse_mode)\n",
        "                    delivered = self._send_response(\n"
        "                        message=message,\n"
        "                        atlas_user_id=atlas_user_id,\n"
        "                        text=response.text,\n"
        "                        parse_mode=response.parse_mode,\n"
        "                    )\n"
        "                    if not delivered:\n"
        "                        self._send_chunks(\n"
        "                            message.user.chat_id,\n"
        "                            response.text,\n"
        "                            response.parse_mode,\n"
        "                        )\n",
    )

    helper = """
    def _send_response(
        self,
        *,
        message: TelegramMessage,
        atlas_user_id: str,
        text: str,
        parse_mode: str | None,
    ) -> bool:
        mode = (
            self.response_mode_store.get(atlas_user_id)
            if self.response_mode_store is not None
            else "automatic"
        )
        audio_available = (
            self.voice_renderer is not None
            and self.voice_renderer.is_available()
        )
        delivery = resolve_delivery_mode(
            configured_mode=mode,
            incoming_media_type=message.media_type,
            audio_available=audio_available,
        )

        if delivery != "audio" or self.voice_renderer is None:
            return False

        self.voice_renderer._current_user = atlas_user_id
        result = self.voice_renderer.render(text)
        if not result.success or result.ogg_path is None:
            return False

        try:
            with self._send_lock:
                self.client.send_voice(
                    chat_id=message.user.chat_id,
                    voice_path=result.ogg_path,
                )
            return True
        except TelegramClientError:
            return False
        finally:
            self.voice_renderer.cleanup(result)

"""
    replace_once(
        polling,
        "    def _send_chunks(self, chat_id: str, text: str, parse_mode: str | None) -> None:\n",
        helper + "    def _send_chunks(self, chat_id: str, text: str, parse_mode: str | None) -> None:\n",
    )

    replace_once(
        runtime,
        "from telegram_interface.storage import TelegramStorage\n",
        "from telegram_interface.storage import TelegramStorage\n"
        "from telegram_interface.response_modes import TelegramResponseModeStore\n"
        "from telegram_interface.voice_delivery import TelegramVoiceRenderer\n"
        "from pathlib import Path\n",
    )

    replace_once(
        runtime,
        "    poller = TelegramPoller(\n        client=client,\n",
        "    response_modes = TelegramResponseModeStore(storage)\n"
        "    project_root = Path(__file__).resolve().parents[1]\n"
        "    voice_renderer = TelegramVoiceRenderer(\n"
        "        project_root=project_root,\n"
        "        user_provider=lambda: getattr(voice_renderer, '_current_user', 'REDACTED_2c7b6821719d'),\n"
        "        personality_provider=lambda: gateway.core.active_personality(\n"
        "            getattr(voice_renderer, '_current_user', 'REDACTED_2c7b6821719d')\n"
        "        ),\n"
        "    )\n"
        "    poller = TelegramPoller(\n"
        "        client=client,\n",
    )

    replace_once(
        runtime,
        "        owner_user_id=\"REDACTED_2c7b6821719d\",\n    )\n",
        "        owner_user_id=\"REDACTED_2c7b6821719d\",\n"
        "        voice_renderer=voice_renderer,\n"
        "        response_mode_store=response_modes,\n"
        "    )\n",
    )

    replace_once(
        response_modes,
        'r"\\b(?:responde|respondeme|contesta|contestame)\\b.*\\b(?:solo|solamente|unicamente)\\b.*\\baudio\\b",',
        'r"\\b(?:responde|respondeme|contesta|contestame)\\b.*\\b(?:solo|solamente|unicamente)\\b.*\\b(?:audio|voz)\\b",',
    )

    print("Integración de voz para Telegram aplicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
