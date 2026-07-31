"""Reinicio completo y seguro de Atlas, incluido Telegram."""

from __future__ import annotations

from pathlib import Path
import subprocess
import threading

from core import context
from commands.admin_policy import require_admin_user

COMMAND = {
    "name": "reinicia atlas",
    "description": "Reinicia Atlas tras una confirmación administrativa reforzada.",
    "category": "Sistema y administración",
    "owner_only": True,
    "capability": "atlas_admin",
    "aliases": [
        "reiniciar atlas",
        "reinicia",
        "reiniciar",
    ],
}

_CONFIRMATIONS = {
    "confirmo reiniciar atlas",
    "confirmar reinicio atlas",
    "si reinicia atlas",
    "sí reinicia atlas",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _has_pending_work(atlas) -> bool:
    confirmations = getattr(atlas, "confirmations", None)
    if confirmations is not None and getattr(confirmations, "pending_confirmation", None) is not None:
        return True
    memory_service = getattr(atlas, "memory_service", None)
    if memory_service is not None and getattr(memory_service, "pending_memory", None) is not None:
        return True
    for name in ("active_tasks", "running_tasks", "pending_tasks", "current_task"):
        value = getattr(atlas, name, None)
        if value:
            return True
    return False


def _is_confirmed(atlas) -> bool:
    text = str(getattr(atlas, "last_original_text", "")).strip().casefold()
    return text in _CONFIRMATIONS


def _launch_restart() -> None:
    script = _project_root() / "scripts" / "restart_atlas.ps1"
    if not script.exists():
        print("No encuentro scripts/restart_atlas.ps1.")
        return
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(_project_root()),
        creationflags=creationflags,
    )


def execute():
    if not require_admin_user():
        return True

    atlas = getattr(context, "atlas", None)
    if atlas is None:
        print("No encuentro la instancia activa de Atlas.")
        return True

    if not _is_confirmed(atlas):
        print()
        if _has_pending_work(atlas):
            print("Tengo una tarea o confirmación pendiente.")
        print("Este reinicio cerrará Atlas y reiniciará también el bot de Telegram.")
        print("Escribe exactamente: confirmo reiniciar atlas")
        return True

    print()
    print("De acuerdo. Voy a reiniciarme. Vuelvo enseguida.")
    threading.Thread(target=_launch_restart, daemon=True).start()
    return False
