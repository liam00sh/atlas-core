"""Reinicio seguro y reforzado del bot de Telegram de Atlas."""

from __future__ import annotations

from pathlib import Path
import subprocess
import threading

from core import context
from commands.admin_policy import require_admin_user

COMMAND = {
    "name": "reinicia telegram",
    "description": "Reinicia el bot de Telegram tras una confirmación administrativa reforzada.",
    "category": "Sistema y administración",
    "owner_only": True,
    "capability": "atlas_admin",
    "aliases": [
        "reiniciar telegram",
        "reinicia el bot de telegram",
        "reiniciar el bot de telegram",
        "reinicia bot telegram",
        "reiniciar bot",
    ],
}

CONFIRMATIONS = {
    "confirmo reiniciar telegram",
    "confirmar reinicio telegram",
    "si reinicia telegram",
    "sí reinicia telegram",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _powershell() -> str:
    return "powershell.exe"


def _start_restart_script() -> None:
    script = _project_root() / "scripts" / "restart_telegram_service.ps1"
    if not script.exists():
        print("No encuentro scripts/restart_telegram_service.ps1.")
        return
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [
            _powershell(),
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
    request_context = getattr(atlas, "channel_request_context", None)
    channel = getattr(request_context, "channel", None) or "cli"
    session_id = getattr(request_context, "session_id", None) or getattr(atlas, "session_id", None) or "local"
    atlas.confirmations.create_confirmation(
        user=atlas.get_user(),
        action_type="administrative_command",
        action_name="restart_telegram",
        arguments={},
        channel=channel,
        session_id=str(session_id),
        accepted_phrases=tuple(CONFIRMATIONS),
    )
    print()
    print("Este reinicio afecta al bot de Telegram y requiere confirmación reforzada.")
    print("Escribe exactamente: confirmo reiniciar telegram")
    return True


def execute_confirmed() -> bool:
    """Ejecuta el reinicio después de que Atlas haya consumido la confirmación."""
    print()
    print("De acuerdo. Voy a reiniciar únicamente el bot de Telegram.")
    print("El supervisor lo levantará de nuevo en unos segundos.")
    threading.Thread(target=_start_restart_script, daemon=True).start()
    return True
