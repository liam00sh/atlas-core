"""Bloqueo local de instancia unica para long polling."""

from __future__ import annotations

import json
import os
from pathlib import Path


class TelegramInstanceLockedError(RuntimeError):
    pass


def _pid_is_matching_bot(pid: int) -> bool:
    """Comprueba que el PID vivo pertenece realmente al bot de Telegram."""
    if pid <= 0:
        return False

    if os.name == "nt":
        try:
            import subprocess

            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    (
                        "$p = Get-CimInstance Win32_Process "
                        f"-Filter \"ProcessId={pid}\"; "
                        "if ($p) { $p.CommandLine }"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=creation_flags,
            )
        except Exception:
            return False

        command_line = completed.stdout.strip().casefold()
        return (
            "python" in command_line
            and "run_telegram_bot.py" in command_line
        )

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class TelegramInstanceLock:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._owned = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"pid": os.getpid()})
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if self._remove_if_stale():
                return self.acquire()
            raise TelegramInstanceLockedError(
                "Ya existe una instancia local de Telegram o un bloqueo aun activo."
            ) from None
        try:
            os.write(descriptor, payload.encode("utf-8"))
        finally:
            os.close(descriptor)
        self._owned = True

    def _remove_if_stale(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            pid = int(data["pid"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return False
        if pid == os.getpid():
            return False

        # Un PID reutilizado por Windows no debe mantener el bloqueo. Solo se
        # conserva si el proceso activo es realmente run_telegram_bot.py.
        if not _pid_is_matching_bot(pid):
            self.path.unlink(missing_ok=True)
            return True
        return False

    def release(self) -> None:
        if self._owned:
            self.path.unlink(missing_ok=True)
            self._owned = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_args):
        self.release()
