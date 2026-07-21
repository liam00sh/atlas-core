"""Configuracion tipada de Telegram obtenida exclusivamente del entorno."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Mapping


_TOKEN_PATTERN = re.compile(r"^[1-9][0-9]{4,15}:[A-Za-z0-9_-]{20,}$")


class TelegramConfigError(ValueError):
    """Configuracion Telegram invalida, sin incluir nunca el token."""


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    enabled: bool
    token: str | None = field(repr=False)
    poll_timeout: int = 30
    link_code_ttl_seconds: int = 600
    rate_limit_per_minute: int = 20
    max_input_characters: int = 8000
    max_concurrent_operations: int = 4
    processing_timeout_seconds: int = 120
    session_ttl_seconds: int = 86400
    delivery_check_seconds: int = 3
    timezone_name: str = "Europe/Madrid"
    data_dir: Path = Path("data/integrations/telegram")
    debug_content_logging: bool = False

    @property
    def token_present(self) -> bool:
        return bool(self.token)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TelegramConfig:
        values = os.environ if env is None else env
        token = values.get("ATLAS_TELEGRAM_BOT_TOKEN", "").strip() or None
        explicit = values.get("ATLAS_TELEGRAM_ENABLED")
        enabled = bool(token) if explicit is None else _parse_bool(explicit, "ATLAS_TELEGRAM_ENABLED")
        config = cls(
            enabled=enabled,
            token=token,
            poll_timeout=_parse_int(values, "ATLAS_TELEGRAM_POLL_TIMEOUT", 30, 1, 50),
            link_code_ttl_seconds=_parse_int(values, "ATLAS_TELEGRAM_LINK_CODE_TTL_SECONDS", 600, 60, 3600),
            rate_limit_per_minute=_parse_int(values, "ATLAS_TELEGRAM_RATE_LIMIT_PER_MINUTE", 20, 1, 300),
            max_input_characters=_parse_int(values, "ATLAS_TELEGRAM_MAX_INPUT_CHARACTERS", 8000, 256, 50000),
            max_concurrent_operations=_parse_int(values, "ATLAS_TELEGRAM_MAX_CONCURRENT_OPERATIONS", 4, 1, 32),
            processing_timeout_seconds=_parse_int(values, "ATLAS_TELEGRAM_PROCESSING_TIMEOUT_SECONDS", 120, 5, 600),
            session_ttl_seconds=_parse_int(values, "ATLAS_TELEGRAM_SESSION_TTL_SECONDS", 86400, 300, 604800),
            delivery_check_seconds=_parse_int(values, "ATLAS_TELEGRAM_DELIVERY_CHECK_SECONDS", 3, 1, 60),
            timezone_name=values.get("ATLAS_TELEGRAM_TIMEZONE", "Europe/Madrid").strip() or "Europe/Madrid",
            data_dir=Path(values.get("ATLAS_TELEGRAM_DATA_DIR", "data/integrations/telegram")),
            debug_content_logging=_parse_bool(values.get("ATLAS_TELEGRAM_DEBUG_CONTENT", "false"), "ATLAS_TELEGRAM_DEBUG_CONTENT"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.enabled and not self.token:
            raise TelegramConfigError("Telegram esta activado, pero falta el token.")
        if self.token and not _TOKEN_PATTERN.fullmatch(self.token):
            raise TelegramConfigError("El token de Telegram no tiene un formato valido.")

    def safe_summary(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "token_present": self.token_present,
            "poll_timeout": self.poll_timeout,
            "link_code_ttl_seconds": self.link_code_ttl_seconds,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "delivery_check_seconds": self.delivery_check_seconds,
            "timezone_name": self.timezone_name,
            "debug_content_logging": self.debug_content_logging,
        }


def _parse_bool(value: str, name: str) -> bool:
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise TelegramConfigError(f"{name} debe ser un valor booleano.")


def _parse_int(values: Mapping[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = values.get(name)
    try:
        value = default if raw is None else int(raw)
    except (TypeError, ValueError) as exc:
        raise TelegramConfigError(f"{name} debe ser un numero entero.") from exc
    if not minimum <= value <= maximum:
        raise TelegramConfigError(f"{name} debe estar entre {minimum} y {maximum}.")
    return value
