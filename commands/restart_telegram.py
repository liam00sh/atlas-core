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

_CONFIRMATIONS = {
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
    if atlas is None or not hasattr(atlas, "confirmations"):
        print("No puedo registrar de forma segura la confirmación del reinicio.")
        return True
    atlas.confirmations.create_confirmation(
        user=atlas.get_user(),
        action_type="telegram_restart",
        action_name="reiniciar Telegram",
        arguments={},
        dangerous=True,
    )
    print()
    print("Este reinicio afecta al bot de Telegram y requiere confirmación reforzada.")
    print("Escribe exactamente: confirmo reiniciar telegram, o cancelar para dejarlo como está.")
    return True


def execute_confirmed():
    print()
    print("De acuerdo. Voy a reiniciar únicamente el bot de Telegram.")
    print("El supervisor lo levantará de nuevo en unos segundos.")
    threading.Thread(target=_start_restart_script, daemon=True).start()
    return True
