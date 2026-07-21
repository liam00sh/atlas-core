"""Cliente minimo y desacoplado para Telegram Bot API."""

from __future__ import annotations

import json
import socket
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramClientError(RuntimeError):
    def __init__(self, message: str, *, code: str = "telegram_api_error", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class TelegramClientProtocol(Protocol):
    def get_updates(self, *, offset: int, timeout: int) -> list[dict[str, Any]]: ...
    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> dict[str, Any]: ...
    def get_me(self) -> dict[str, Any]: ...
    def get_webhook_info(self) -> dict[str, Any]: ...


class TelegramBotClient:
    """Adaptador HTTP sin dependencias externas; nunca expone el token."""

    def __init__(self, token: str, *, api_base: str = "https://api.telegram.org", opener=urlopen) -> None:
        if not token:
            raise ValueError("Falta el token de Telegram.")
        self.__token = token
        self._base_url = f"{api_base.rstrip('/')}/bot{token}"
        self._opener = opener

    def __repr__(self) -> str:
        return "TelegramBotClient(token_present=True)"

    def _call(self, method: str, parameters: dict[str, Any] | None = None, *, timeout: int = 30) -> Any:
        payload = urlencode(parameters or {}).encode("utf-8")
        request = Request(f"{self._base_url}/{method}", data=payload, method="POST")
        try:
            with self._opener(request, timeout=timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise TelegramClientError(
                f"Telegram rechazo la operacion HTTP {exc.code}.",
                code=f"telegram_http_{exc.code}",
                retryable=exc.code == 429 or exc.code >= 500,
            ) from None
        except (URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError):
            raise TelegramClientError(
                "No se pudo comunicar de forma valida con Telegram.",
                code="telegram_unavailable",
                retryable=True,
            ) from None
        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            error_code = decoded.get("error_code") if isinstance(decoded, dict) else None
            raise TelegramClientError(
                "Telegram devolvio un resultado no valido.",
                code=f"telegram_api_{error_code or 'unknown'}",
                retryable=error_code == 429 or bool(error_code and error_code >= 500),
            )
        return decoded.get("result")

    def get_updates(self, *, offset: int, timeout: int) -> list[dict[str, Any]]:
        result = self._call(
            "getUpdates",
            {"offset": offset, "timeout": timeout, "allowed_updates": json.dumps(["message"])},
            timeout=timeout + 10,
        )
        return result if isinstance(result, list) else []

    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> dict[str, Any]:
        parameters: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            parameters["parse_mode"] = parse_mode
        result = self._call("sendMessage", parameters, timeout=30)
        return result if isinstance(result, dict) else {}

    def get_me(self) -> dict[str, Any]:
        result = self._call("getMe", timeout=15)
        return result if isinstance(result, dict) else {}

    def get_webhook_info(self) -> dict[str, Any]:
        result = self._call("getWebhookInfo", timeout=15)
        return result if isinstance(result, dict) else {}
