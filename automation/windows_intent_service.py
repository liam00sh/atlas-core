"""
Proyecto Atlas
Archivo: automation/windows_intent_service.py

Servicio que conecta el resolver determinista con AutomationManager.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from automation.automation_manager import AutomationManager
from automation.windows_intent_resolver import (
    ResolvedWindowsIntent,
    WindowsIntentResolver,
)


@dataclass(frozen=True, slots=True)
class WindowsIntentExecution:
    handled: bool
    success: bool
    message: str
    action_id: str | None = None
    result: Any = None
    error_code: str = ""


class WindowsIntentService:
    def __init__(
        self,
        manager: AutomationManager,
        resolver: WindowsIntentResolver | None = None,
    ) -> None:
        self.manager = manager
        self.resolver = resolver or WindowsIntentResolver()

    def handle(
        self,
        text: str,
        *,
        user_id: str,
        channel: str,
    ) -> WindowsIntentExecution:
        resolved = self.resolver.resolve(text)
        if resolved is None:
            return WindowsIntentExecution(
                handled=False,
                success=False,
                message="",
            )

        try:
            automation = self.manager.create(
                action_id=resolved.action_id,
                owner_user_id=user_id,
                creator_user_id=user_id,
                parameters=dict(resolved.parameters),
            )
        except PermissionError:
            return WindowsIntentExecution(
                handled=True,
                success=False,
                message="No tienes permiso para realizar esa acción.",
                action_id=resolved.action_id,
                error_code="permission_denied",
            )
        except (TypeError, ValueError) as exc:
            return WindowsIntentExecution(
                handled=True,
                success=False,
                message=f"No puedo ejecutar esa acción: {exc}",
                action_id=resolved.action_id,
                error_code=type(exc).__name__,
            )

        execution = self.manager.execute(
            automation.automation_id,
            requested_by_user_id=user_id,
            channel=channel,
        )

        if not execution.success:
            return WindowsIntentExecution(
                handled=True,
                success=False,
                message=self._failure_message(resolved, execution.error_code),
                action_id=resolved.action_id,
                result=execution,
                error_code=execution.error_code,
            )

        return WindowsIntentExecution(
            handled=True,
            success=True,
            message=self._success_message(resolved, execution.result),
            action_id=resolved.action_id,
            result=execution.result,
        )

    @staticmethod
    def _success_message(
        intent: ResolvedWindowsIntent,
        result: Any,
    ) -> str:
        if intent.action_id == "windows.application.open":
            app_id = str(intent.parameters.get("app_id", ""))
            names = {
                "calculator": "la calculadora",
                "notepad": "el Bloc de notas",
            }
            return f"He abierto {names.get(app_id, 'la aplicación')}."

        if intent.action_id == "windows.disk.space.read":
            payload = _unwrap_result(result)
            free_bytes = payload.get("free_bytes")
            if isinstance(free_bytes, int):
                return f"Tienes {_format_bytes(free_bytes)} libres."
            return "He consultado el espacio disponible."

        if intent.action_id == "windows.process.status.read":
            payload = _unwrap_result(result)
            running = bool(payload.get("running"))
            return (
                "Telegram está abierto."
                if running
                else "Telegram no está abierto."
            )

        return "Acción completada."

    @staticmethod
    def _failure_message(
        intent: ResolvedWindowsIntent,
        error_code: str,
    ) -> str:
        if error_code == "permission_denied":
            return "No tienes permiso para realizar esa acción."
        if error_code == "WindowsActionError":
            return "No he podido ejecutar esa acción en Windows."
        return "La acción no ha podido completarse."


def _unwrap_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        nested = result.get("result")
        if isinstance(nested, dict):
            return nested
        return result
    return {}


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit in {"GB", "TB"}:
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{value} B"
