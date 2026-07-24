"""Factoría segura de clientes de Home Assistant."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from automation.home_assistant_client import (
    BaseHomeAssistantClient,
    HomeAssistantHttpClient,
)
from automation.home_assistant_models import HomeEntityState
from automation.home_assistant_simulator import HomeAssistantSimulator


@dataclass(frozen=True, slots=True)
class HomeAssistantSettings:
    mode: str = "simulated"
    url: str = ""
    token: str = ""
    timeout_seconds: float = 10.0
    verify_ssl: bool = False


def _parse_bool(value: str, *, default: bool) -> bool:
    normalized = str(value).strip().casefold()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "on", "si", "sí"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Valor booleano no válido: {value!r}")


def load_env_file(path: str | Path) -> dict[str, str]:
    """Carga pares simples KEY=VALUE sin registrar ni exponer secretos."""
    values: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def load_home_assistant_settings(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: str | Path | None = None,
) -> HomeAssistantSettings:
    values = dict(load_env_file(env_file)) if env_file is not None else {}
    values.update(dict(os.environ if environ is None else environ))

    mode = values.get("HOME_ASSISTANT_MODE", "simulated").strip().casefold()
    if mode not in {"simulated", "real"}:
        raise ValueError("HOME_ASSISTANT_MODE debe ser 'simulated' o 'real'.")

    timeout_raw = values.get("HOME_ASSISTANT_TIMEOUT", "10")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ValueError("HOME_ASSISTANT_TIMEOUT debe ser numérico.") from exc

    settings = HomeAssistantSettings(
        mode=mode,
        url=values.get("HOME_ASSISTANT_URL", "").strip(),
        token=values.get("HOME_ASSISTANT_TOKEN", "").strip(),
        timeout_seconds=timeout_seconds,
        verify_ssl=_parse_bool(
            values.get("HOME_ASSISTANT_VERIFY_SSL", "false"),
            default=False,
        ),
    )
    if settings.mode == "real":
        if not settings.url:
            raise ValueError("HOME_ASSISTANT_URL es obligatorio en modo real.")
        if not settings.token:
            raise ValueError("HOME_ASSISTANT_TOKEN es obligatorio en modo real.")
    return settings


def create_home_assistant_client(
    settings: HomeAssistantSettings,
    *,
    initial_states: dict[str, HomeEntityState] | None = None,
) -> BaseHomeAssistantClient:
    if settings.mode == "simulated":
        return HomeAssistantSimulator(initial_states)
    return HomeAssistantHttpClient(
        base_url=settings.url,
        token=settings.token,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )
