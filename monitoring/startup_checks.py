"""Checks de inicio diferenciando servicios locales y remotos."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import Callable

from monitoring.models import HealthCheckResult, HealthState


@dataclass(slots=True, frozen=True)
class StartupCheck:
    label: str
    ok: bool
    status: str
    critical: bool = False


def check_local_docker() -> StartupCheck:
    installed = shutil.which("docker") is not None
    if installed:
        return StartupCheck(
            label="Docker local",
            ok=True,
            status="instalado",
        )
    return StartupCheck(
        label="Docker local",
        ok=True,
        status="no utilizado en este PC",
    )


def check_home_assistant(
    is_available: Callable[[], bool] | None,
) -> StartupCheck:
    if is_available is None:
        return StartupCheck(
            label="Home Assistant",
            ok=False,
            status="no configurado",
            critical=False,
        )
    try:
        available = bool(is_available())
    except Exception:
        available = False
    return StartupCheck(
        label="Home Assistant",
        ok=available,
        status="API accesible" if available else "no disponible; Atlas continuará en modo degradado",
        critical=False,
    )


def check_raspberry(
    checker: Callable[[], HealthCheckResult] | None,
) -> StartupCheck:
    if checker is None:
        return StartupCheck(
            label="Raspberry Pi",
            ok=False,
            status="no configurada",
            critical=False,
        )
    try:
        result = checker()
    except Exception:
        result = None
    ok = bool(result and result.state in {HealthState.OK, HealthState.WARNING})
    return StartupCheck(
        label="Raspberry Pi",
        ok=ok,
        status=(
            result.message
            if result is not None and result.message
            else "no disponible; Atlas continuará en modo degradado"
        ),
        critical=False,
    )
