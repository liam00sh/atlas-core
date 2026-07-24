"""Reinicio seguro y reforzado del bot de Telegram de Atlas."""

from __future__ import annotations

from pathlib import Path
import subprocess
import threading

from core import context
from commands.admin_policy import require_admin_user

COMMAND = {
    "name": "reinicia telegram",
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


def _is_confirmed() -> bool:
    atlas = getattr(context, "atlas", None)
    text = str(getattr(atlas, "last_original_text", "")).strip().casefold()
    return text in _CONFIRMATIONS


def execute():
    if not require_admin_user():
        return True

    if not _is_confirmed():
        print()
        print("Este reinicio afecta al bot de Telegram y requiere confirmación reforzada.")
        print("Escribe exactamente: confirmo reiniciar telegram")
        return True

    print()
    print("De acuerdo. Voy a reiniciar únicamente el bot de Telegram.")
    print("El supervisor lo levantará de nuevo en unos segundos.")
    threading.Thread(target=_start_restart_script, daemon=True).start()
    return True
