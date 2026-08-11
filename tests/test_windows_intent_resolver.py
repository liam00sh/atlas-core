"""Pruebas del Windows Intent Resolver y su ejecución integrada."""

from pathlib import Path
import platform

import pytest

from automation.stage_d_bootstrap import build_stage_d_manager
from automation.windows_intent_resolver import WindowsIntentResolver
from automation.windows_intent_service import WindowsIntentService


@pytest.mark.parametrize(
    ("text", "action_id", "parameters"),
    (
        (
            "Abre la calculadora",
            "windows.application.open",
            {"app_id": "calculator"},
        ),
        (
            "Daxter, abre el bloc de notas",
            "windows.application.open",
            {"app_id": "notepad"},
        ),
        (
            "¿Cuánto espacio libre tengo?",
            "windows.disk.space.read",
            {},
        ),
        (
            "¿Está abierto Telegram?",
            "windows.process.status.read",
            {"process_name": "Telegram.exe"},
        ),
    ),
)
def test_resolver_maps_supported_phrases(
    text: str,
    action_id: str,
    parameters: dict[str, object],
) -> None:
    resolved = WindowsIntentResolver().resolve(text)

    assert resolved is not None
    assert resolved.action_id == action_id
    assert dict(resolved.parameters) == parameters
    assert resolved.confidence == 1.0


@pytest.mark.parametrize(
    "text",
    (
        "Abre PowerShell",
        "Ejecuta dir C:\\",
        "Borra todos mis archivos",
        "Haz lo que quieras en Windows",
    ),
)
def test_resolver_rejects_unsupported_or_dangerous_phrases(
    text: str,
) -> None:
    assert WindowsIntentResolver().resolve(text) is None


def _service(tmp_path: Path) -> WindowsIntentService:
    manager = build_stage_d_manager(
        storage_path=tmp_path / "automations.json",
        audit_path=tmp_path / "audit.jsonl",
        include_stage_c=False,
    )
    return WindowsIntentService(manager)


def test_Alex_can_request_disk_space(tmp_path: Path) -> None:
    result = _service(tmp_path).handle(
        "Cuánto espacio libre tengo",
        user_id="Alex",
        channel="test",
    )

    assert result.handled is True
    assert result.success is True
    assert result.action_id == "windows.disk.space.read"


def test_Carla_is_blocked_from_opening_apps(tmp_path: Path) -> None:
    result = _service(tmp_path).handle(
        "Abre la calculadora",
        user_id="Carla",
        channel="test",
    )

    assert result.handled is True
    assert result.success is False
    assert result.error_code == "permission_denied"


def test_unknown_text_falls_through(tmp_path: Path) -> None:
    result = _service(tmp_path).handle(
        "Qué tiempo hace",
        user_id="Alex",
        channel="test",
    )

    assert result.handled is False


@pytest.mark.skipif(
    platform.system().casefold() != "windows",
    reason="La apertura real solo se valida en Windows.",
)
def test_Alex_can_open_calculator_on_windows(tmp_path: Path) -> None:
    result = _service(tmp_path).handle(
        "Daxter, abre la calculadora",
        user_id="Alex",
        channel="test",
    )

    assert result.handled is True
    assert result.success is True
    assert result.action_id == "windows.application.open"
