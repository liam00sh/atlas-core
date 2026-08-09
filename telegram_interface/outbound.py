"""Envío multimedia limitado a raíces controladas y cuentas vinculadas."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePath
from time import perf_counter
from typing import Callable, Mapping

from telegram_interface.media import TelegramMediaError, TelegramMediaValidator


class TelegramOutboundError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TelegramOutboundResult:
    media_type: str
    mime_type: str
    byte_size: int
    duration_ms: float


class TelegramOutboundMediaService:
    def __init__(
        self,
        *,
        client,
        account_resolver: Callable[[str], Mapping[str, object] | None],
        allowed_roots: Mapping[str, str | Path],
        max_bytes: Mapping[str, int] | None = None,
        audit: Callable[[str, int, str], None] | None = None,
    ) -> None:
        self.client = client
        self.account_resolver = account_resolver
        self.allowed_roots = {name: Path(path).resolve() for name, path in allowed_roots.items()}
        self.max_bytes = dict(max_bytes or {
            "photo": 12 * 1024 * 1024,
            "voice": 12 * 1024 * 1024,
            "audio": 25 * 1024 * 1024,
            "document": 20 * 1024 * 1024,
        })
        self.audit = audit or (lambda _kind, _size, _result: None)
        self.validator = TelegramMediaValidator()

    def send(
        self,
        *,
        requested_by: str,
        media_type: str,
        root_name: str,
        relative_path: str,
        contains_personal_data: bool = False,
        confirmed: bool = False,
        delete_after_send: bool = False,
    ) -> TelegramOutboundResult:
        if contains_personal_data and not confirmed:
            raise TelegramOutboundError("confirmation_required", "Los datos personales requieren confirmación explícita.")
        account = self.account_resolver(requested_by)
        if not account or account.get("state") != "linked" or not account.get("chat_id"):
            raise TelegramOutboundError("recipient_not_linked", "El usuario no tiene un chat Telegram vinculado.")
        target = self._resolve(root_name, relative_path)
        limit = int(self.max_bytes.get(media_type, 0))
        if limit <= 0:
            raise TelegramOutboundError("media_type_denied", "El tipo de envío no está permitido.")
        try:
            mime, size, _digest = self.validator.validate(target, media_type=media_type, max_bytes=limit)
        except TelegramMediaError as exc:
            self.audit(media_type, 0, exc.code)
            raise TelegramOutboundError(exc.code, str(exc)) from exc
        started = perf_counter()
        try:
            method = getattr(self.client, f"send_{media_type}")
            method(chat_id=str(account["chat_id"]), path=target)
        except Exception as exc:
            self.audit(media_type, size, "error")
            raise TelegramOutboundError("telegram_upload_failed", "No se pudo enviar el archivo.") from exc
        finally:
            if delete_after_send:
                self._delete_generated(target, root_name)
        elapsed = round((perf_counter() - started) * 1000, 3)
        self.audit(media_type, size, "ok")
        return TelegramOutboundResult(media_type, mime, size, elapsed)

    def _resolve(self, root_name: str, relative_path: str) -> Path:
        root = self.allowed_roots.get(str(root_name))
        if root is None:
            raise TelegramOutboundError("root_denied", "La raíz de salida no está permitida.")
        raw = str(relative_path).strip()
        pure = PurePath(raw)
        if not raw or pure.is_absolute() or ".." in pure.parts:
            raise TelegramOutboundError("path_denied", "La ruta de salida no es relativa y segura.")
        target = (root / pure).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise TelegramOutboundError("path_denied", "La ruta sale de la raíz permitida.") from exc
        if not target.is_file():
            raise TelegramOutboundError("file_missing", "El archivo no existe dentro de la raíz permitida.")
        # resolve() también atraviesa enlaces; relative_to impide que un enlace
        # simbólico apunte fuera de la raíz.
        return target

    def _delete_generated(self, target: Path, root_name: str) -> None:
        # Solo la raíz explícita "generated" admite borrado post-envío.
        if root_name != "generated":
            return
        try:
            target.relative_to(self.allowed_roots[root_name])
            target.unlink(missing_ok=True)
        except (KeyError, OSError, ValueError):
            pass
