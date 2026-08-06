"""Cliente minimo y desacoplado para Telegram Bot API."""

from __future__ import annotations

import json
import secrets
import socket
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TelegramClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "telegram_api_error",
        retryable: bool = False,
        kind: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.kind = kind or ("transient" if retryable else "permanent")
        self.retry_after = retry_after


class TelegramClientProtocol(Protocol):
    def get_updates(self, *, offset: int, timeout: int) -> list[dict[str, Any]]: ...
    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> dict[str, Any]: ...
    def get_me(self) -> dict[str, Any]: ...
    def get_webhook_info(self) -> dict[str, Any]: ...
    def get_file(self, *, file_id: str) -> dict[str, Any]: ...
    def download_file(self, *, file_path: str, destination: str | Path, max_bytes: int) -> Path: ...
    def send_voice(self, *, chat_id: str, path: str | Path) -> dict[str, Any]: ...
    def send_audio(self, *, chat_id: str, path: str | Path) -> dict[str, Any]: ...
    def send_photo(self, *, chat_id: str, path: str | Path) -> dict[str, Any]: ...
    def send_document(self, *, chat_id: str, path: str | Path) -> dict[str, Any]: ...


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
            retryable = exc.code == 429 or exc.code >= 500
            raise TelegramClientError(
                f"Telegram rechazo la operacion HTTP {exc.code}.",
                code=f"telegram_http_{exc.code}",
                retryable=retryable,
                kind="rate_limit" if exc.code == 429 else ("transient" if retryable else "permanent"),
            ) from None
        except (URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError):
            raise TelegramClientError(
                "No se pudo comunicar de forma valida con Telegram.",
                code="telegram_unavailable",
                retryable=True,
                kind="transient",
            ) from None
        if not isinstance(decoded, dict) or decoded.get("ok") is not True:
            error_code = decoded.get("error_code") if isinstance(decoded, dict) else None
            retry_after = None
            parameters = decoded.get("parameters") if isinstance(decoded, dict) else None
            if isinstance(parameters, dict) and parameters.get("retry_after") is not None:
                try:
                    retry_after = max(0.0, float(parameters["retry_after"]))
                except (TypeError, ValueError):
                    retry_after = None
            retryable = error_code == 429 or bool(error_code and error_code >= 500)
            raise TelegramClientError(
                "Telegram devolvio un resultado no valido.",
                code=f"telegram_api_{error_code or 'unknown'}",
                retryable=retryable,
                kind="rate_limit" if error_code == 429 else ("transient" if retryable else "permanent"),
                retry_after=retry_after,
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

    def get_file(self, *, file_id: str) -> dict[str, Any]:
        result = self._call("getFile", {"file_id": file_id}, timeout=30)
        return result if isinstance(result, dict) else {}

    def download_file(self, *, file_path: str, destination: str | Path, max_bytes: int) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self._base_url.rsplit('/bot', 1)[0]}/file/bot{self.__token}/{file_path.lstrip('/')}"
        request = Request(url, method="GET")
        try:
            with self._opener(request, timeout=60) as response:
                declared = int(response.headers.get("Content-Length") or 0)
                if declared and declared > max_bytes:
                    raise TelegramClientError("El archivo supera el límite permitido.", code="media_too_large")
                temporary = target.with_suffix(target.suffix + ".part")
                total = 0
                with temporary.open("wb") as stream:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > max_bytes:
                            stream.close()
                            temporary.unlink(missing_ok=True)
                            raise TelegramClientError("El archivo supera el límite permitido.", code="media_too_large")
                        stream.write(chunk)
                temporary.replace(target)
                return target
        except TelegramClientError:
            raise
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise TelegramClientError("No se pudo descargar el archivo de Telegram.", code="media_download_failed", retryable=True) from exc

    def send_voice(self, *, chat_id: str, path: str | Path) -> dict[str, Any]:
        return self._upload("sendVoice", "voice", chat_id, path, "audio/ogg")

    def send_audio(self, *, chat_id: str, path: str | Path) -> dict[str, Any]:
        return self._upload("sendAudio", "audio", chat_id, path, "audio/mpeg")

    def send_photo(self, *, chat_id: str, path: str | Path) -> dict[str, Any]:
        return self._upload("sendPhoto", "photo", chat_id, path, "image/jpeg")

    def send_document(self, *, chat_id: str, path: str | Path) -> dict[str, Any]:
        return self._upload("sendDocument", "document", chat_id, path, "application/octet-stream")

    def _upload(self, method: str, field: str, chat_id: str, path: str | Path, content_type: str) -> dict[str, Any]:
        target = Path(path)
        if not target.is_file():
            raise TelegramClientError("El archivo de salida no existe.", code="upload_missing")
        boundary = f"atlas-{secrets.token_hex(16)}"
        body = bytearray()

        def append(value: bytes) -> None:
            body.extend(value)

        append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode())
        append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"media\"\r\nContent-Type: {content_type}\r\n\r\n".encode())
        append(target.read_bytes())
        append(f"\r\n--{boundary}--\r\n".encode())
        request = Request(
            f"{self._base_url}/{method}",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=60) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
            raise TelegramClientError("No se pudo enviar el archivo a Telegram.", code="telegram_upload_failed", retryable=True) from exc
        if not isinstance(decoded, dict) or decoded.get("ok") is not True or not isinstance(decoded.get("result"), dict):
            raise TelegramClientError("Telegram rechazó el archivo.", code="telegram_upload_rejected")
        return decoded["result"]
