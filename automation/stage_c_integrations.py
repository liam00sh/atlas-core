"""Integraciones reales y seguras de la Etapa C.

Este módulo no crea dependencias fuertes con Telegram, Ollama o Drive.
Recibe las instancias reales ya configuradas por Atlas y construye probes,
proveedores y planes cerrados a partir de sus interfaces públicas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import json
import shutil
import socket
import zipfile

from automation.backup_adapter import BackupPlan
from automation.notification_adapter import NotificationProvider
from automation.service_monitor import ServiceProbe
from automation.technical_routines import RoutineStep, TechnicalRoutine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_atlas_probe(
    *,
    version_getter: Callable[[], str] | None = None,
    started_getter: Callable[[], bool] | None = None,
) -> ServiceProbe:
    def check() -> dict[str, Any]:
        started = True if started_getter is None else bool(started_getter())
        details: dict[str, Any] = {
            "available": started,
            "hostname": socket.gethostname(),
        }
        if version_getter is not None:
            details["version"] = str(version_getter())
        return details

    return ServiceProbe(
        service_id="atlas",
        display_name="Atlas Core",
        checker=check,
        critical=True,
    )


def build_telegram_probe(client: Any) -> ServiceProbe:
    """Usa TelegramBotClient.get_me() si está disponible."""

    def check() -> dict[str, Any]:
        get_me = getattr(client, "get_me", None)
        if not callable(get_me):
            return {
                "available": False,
                "reason": "get_me_not_available",
            }

        info = get_me()
        if not isinstance(info, dict):
            return {
                "available": bool(info),
            }

        username = info.get("username")
        bot_id = info.get("id")
        return {
            "available": True,
            "username": username,
            "bot_id": bot_id,
        }

    return ServiceProbe(
        service_id="telegram",
        display_name="Telegram",
        checker=check,
        critical=True,
    )


def build_ollama_probe(provider: Any) -> ServiceProbe:
    """Usa BaseAIProvider.is_available() sin generar texto."""

    def check() -> dict[str, Any]:
        method = getattr(provider, "is_available", None)
        if not callable(method):
            return {
                "available": False,
                "reason": "is_available_not_found",
            }
        available = bool(method())
        details: dict[str, Any] = {"available": available}
        model = getattr(provider, "model", None)
        if model:
            details["model"] = str(model)
        return details

    return ServiceProbe(
        service_id="ollama",
        display_name="Ollama",
        checker=check,
        critical=False,
    )


def build_drive_probe(client: Any) -> ServiceProbe:
    """Comprueba el cliente real mediante una operación de lectura mínima."""

    def check() -> dict[str, Any]:
        # Preferimos un método explícito de disponibilidad si existe.
        for name in ("is_available", "health_check", "check_connection"):
            method = getattr(client, name, None)
            if callable(method):
                result = method()
                if isinstance(result, dict):
                    payload = dict(result)
                    payload.setdefault(
                        "available",
                        bool(payload.get("ok", False)),
                    )
                    return payload
                return {"available": bool(result)}

        # GoogleDriveApiClient expone normalmente list_folder o search.
        list_folder = getattr(client, "list_folder", None)
        if callable(list_folder):
            try:
                result = list_folder(None)
            except TypeError:
                result = list_folder("")
            return {
                "available": result is not None,
                "operation": "list_folder",
            }

        search = getattr(client, "search", None)
        if callable(search):
            try:
                result = search("Atlas")
            except TypeError:
                result = search(query="Atlas")
            return {
                "available": result is not None,
                "operation": "search",
            }

        return {
            "available": False,
            "reason": "supported_read_method_not_found",
        }

    return ServiceProbe(
        service_id="drive",
        display_name="Google Drive",
        checker=check,
        critical=False,
    )


def build_pc_status_probe(
    status_path: str | Path,
    *,
    stale_after_seconds: int = 180,
) -> ServiceProbe:
    path = Path(status_path)

    def check() -> dict[str, Any]:
        if not path.exists():
            return {
                "available": False,
                "reason": "status_file_not_found",
                "path": str(path),
            }

        payload = json.loads(path.read_text(encoding="utf-8"))
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        )
        age_seconds = (
            datetime.now(timezone.utc) - modified_at
        ).total_seconds()

        return {
            "available": age_seconds <= stale_after_seconds,
            "age_seconds": round(age_seconds, 2),
            "stale_after_seconds": stale_after_seconds,
            "status": payload,
        }

    return ServiceProbe(
        service_id="pc_monitor",
        display_name="Monitor del PC",
        checker=check,
        critical=False,
    )


def build_disk_probe(
    target_path: str | Path,
    *,
    minimum_free_percent: float = 10.0,
) -> ServiceProbe:
    path = Path(target_path)

    def check() -> dict[str, Any]:
        usage = shutil.disk_usage(path)
        free_percent = (usage.free / usage.total) * 100
        return {
            "available": free_percent >= minimum_free_percent,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_percent": round(free_percent, 2),
            "minimum_free_percent": minimum_free_percent,
            "path": str(path),
        }

    return ServiceProbe(
        service_id="disk",
        display_name="Espacio en disco",
        checker=check,
        critical=True,
    )


@dataclass(slots=True)
class TelegramPrivateNotificationProvider(NotificationProvider):
    """Envía una notificación mediante el cliente Telegram ya autenticado."""

    client: Any
    recipient_resolver: Callable[[str], int | str | None]

    def send(self, recipient_user_id: str, message: str) -> bool:
        chat_id = self.recipient_resolver(recipient_user_id)
        if chat_id is None:
            return False

        for method_name in ("send_message", "send_text", "send"):
            method = getattr(self.client, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(chat_id, message)
            except TypeError:
                result = method(
                    chat_id=chat_id,
                    text=message,
                )
            return result is not False
        raise AttributeError(
            "El cliente Telegram no expone un método de envío compatible."
        )


def build_manual_project_backup_plan(
    *,
    project_root: str | Path,
    destination_dir: str | Path,
    plan_id: str = "atlas.manual",
    exclude_names: set[str] | None = None,
) -> BackupPlan:
    source = Path(project_root).resolve()
    destination = Path(destination_dir).resolve()
    excluded = set(exclude_names or {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "venv",
        ".venv",
    })

    def runner() -> dict[str, Any]:
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(
                f"No existe la raíz del proyecto: {source}"
            )

        destination.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = destination / f"atlas_manual_{timestamp}.zip"

        file_count = 0
        total_bytes = 0
        with zipfile.ZipFile(
            archive,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as handle:
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(source)
                if any(part in excluded for part in relative.parts):
                    continue
                if destination in path.parents:
                    continue
                handle.write(path, relative)
                file_count += 1
                total_bytes += path.stat().st_size

        # Verificación estructural del ZIP.
        with zipfile.ZipFile(archive, mode="r") as handle:
            corrupt_member = handle.testzip()

        if corrupt_member is not None:
            raise OSError(
                f"La copia contiene un archivo corrupto: {corrupt_member}"
            )

        return {
            "archive": str(archive),
            "file_count": file_count,
            "source_bytes": total_bytes,
            "archive_bytes": archive.stat().st_size,
            "verified": True,
            "created_at": _utc_now_iso(),
        }

    return BackupPlan(
        plan_id=plan_id,
        display_name="Copia manual del Proyecto Atlas",
        runner=runner,
        allowed=True,
    )


def build_health_check_routine(
    *,
    service_summary: Callable[[], dict[str, Any]],
    backup_status_getter: Callable[[], Any] | None = None,
) -> TechnicalRoutine:
    steps = [
        RoutineStep(
            step_id="services",
            runner=lambda params: service_summary(),
        )
    ]
    if backup_status_getter is not None:
        steps.append(
            RoutineStep(
                step_id="backup_status",
                runner=lambda params: backup_status_getter(),
                continue_on_error=True,
            )
        )

    return TechnicalRoutine(
        routine_id="atlas.health.check",
        name="Diagnóstico técnico de Atlas",
        steps=tuple(steps),
    )
