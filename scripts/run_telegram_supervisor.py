"""Supervisor residente de Atlas Telegram para Windows.

Mantiene el bot en segundo plano, lo reinicia si termina y recarga el código
cuando detecta cambios en archivos fuente relevantes. No depende de una
terminal abierta.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import py_compile
import sys
import time
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_BOT = PROJECT_ROOT / "scripts" / "run_telegram_bot.py"
STATE_DIR = PROJECT_ROOT / "data" / "integrations" / "telegram"
LOG_DIR = PROJECT_ROOT / "logs" / "telegram"
SUPERVISOR_LOCK = STATE_DIR / "supervisor.lock"
SUPERVISOR_LOG = LOG_DIR / "telegram_supervisor.log"
BOT_LOG = LOG_DIR / "telegram_service.log"
POLLING_LOCK = STATE_DIR / "polling.lock"
STATUS_FILE = STATE_DIR / "supervisor_status.json"

WATCH_ROOTS = (
    "core",
    "telegram_interface",
    "assistant_identity",
    "conversation",
    "memory",
    "knowledge",
    "tools",
    "ai",
)
WATCH_FILES = (
    "config.py",
    ".env",
)
WATCH_SUFFIXES = {".py", ".json", ".yaml", ".yml", ".toml"}
EXCLUDED_PARTS = {"__pycache__", ".git", ".agents", "tests", "logs", "data", "backups"}

POLL_SECONDS = 2.0
DEBOUNCE_SECONDS = 2.0
RESTART_DELAY_SECONDS = 3.0
GRACEFUL_STOP_SECONDS = 15.0

_stop_requested = False
_restart_count = 0
_last_exit_code: int | None = None


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with SUPERVISOR_LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"{timestamp} {message}\n")




def _write_status(state: str, process: subprocess.Popen[bytes] | None = None) -> None:
    """Publica un latido atómico para diagnóstico sin inspeccionar procesos."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": state,
        "supervisor_pid": os.getpid(),
        "bot_pid": process.pid if process is not None and process.poll() is None else None,
        "heartbeat": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "restart_count": _restart_count,
        "last_exit_code": _last_exit_code,
        "python": sys.executable,
    }
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATUS_FILE)


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # En Windows algunos procesos no permiten la comprobación, pero pueden
        # seguir vivos. Conservamos el bloqueo por seguridad.
        return True
    return True


def _acquire_supervisor_lock() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if SUPERVISOR_LOCK.exists():
        try:
            payload = json.loads(SUPERVISOR_LOCK.read_text(encoding="utf-8"))
            previous_pid = int(payload.get("pid", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            previous_pid = 0
        if previous_pid and _pid_is_alive(previous_pid):
            raise RuntimeError("Ya existe un supervisor de Atlas Telegram activo.")
        SUPERVISOR_LOCK.unlink(missing_ok=True)

    descriptor = os.open(SUPERVISOR_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, json.dumps({"pid": os.getpid()}).encode("utf-8"))
    finally:
        os.close(descriptor)


def _release_supervisor_lock() -> None:
    try:
        payload = json.loads(SUPERVISOR_LOCK.read_text(encoding="utf-8"))
        if int(payload.get("pid", 0)) == os.getpid():
            SUPERVISOR_LOCK.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass


def _iter_watch_files() -> Iterable[Path]:
    for relative in WATCH_FILES:
        path = PROJECT_ROOT / relative
        if path.is_file():
            yield path

    scripts_dir = PROJECT_ROOT / "scripts"
    if scripts_dir.is_dir():
        for path in scripts_dir.glob("*.py"):
            if path.is_file():
                yield path

    for relative in WATCH_ROOTS:
        root = PROJECT_ROOT / relative
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in WATCH_SUFFIXES:
                continue
            relative_parts = set(path.relative_to(PROJECT_ROOT).parts)
            if relative_parts & EXCLUDED_PARTS:
                continue
            yield path


def _snapshot() -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for path in _iter_watch_files():
        try:
            stat = path.stat()
        except OSError:
            continue
        result[str(path)] = (stat.st_mtime_ns, stat.st_size)
    return result


def _sources_compile() -> tuple[bool, str]:
    """Evita matar el bot sano mientras Drive está copiando un archivo parcial."""
    for path in _iter_watch_files():
        if path.suffix.lower() != ".py":
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            return False, f"{path}: {exc.msg}"
        except OSError as exc:
            return False, f"{path}: {exc}"
    return True, ""

def _clear_stale_polling_lock() -> None:
    """Elimina polling.lock únicamente cuando su PID ya no está activo."""
    if not POLLING_LOCK.exists():
        return
    try:
        payload = json.loads(POLLING_LOCK.read_text(encoding="utf-8"))
        pid = int(payload.get("pid", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pid = 0
    if pid and _pid_is_alive(pid):
        _log(f"polling.lock pertenece a un proceso activo PID={pid}; no se elimina.")
        return
    try:
        POLLING_LOCK.unlink(missing_ok=True)
        _log("polling.lock obsoleto eliminado.")
    except OSError as exc:
        _log(f"No se pudo limpiar polling.lock: {exc}")

def _start_bot(log_stream) -> subprocess.Popen[bytes]:
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    command = [sys.executable, str(RUN_BOT)]
    _log("Iniciando proceso Atlas Telegram.")
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
        env=os.environ.copy(),
    )


def _stop_bot(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    _log(f"Deteniendo proceso Atlas Telegram PID={process.pid}.")
    process.terminate()
    try:
        process.wait(timeout=GRACEFUL_STOP_SECONDS)
    except subprocess.TimeoutExpired:
        _log("El proceso no terminó a tiempo; se fuerza su cierre.")
        process.kill()
        process.wait(timeout=5)
    _clear_stale_polling_lock()


def _handle_stop(_signum, _frame) -> None:
    global _stop_requested
    _stop_requested = True


def main() -> int:
    if not RUN_BOT.is_file():
        print(f"No existe {RUN_BOT}")
        return 10

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _acquire_supervisor_lock()
    except RuntimeError as exc:
        _log(str(exc))
        return 11

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    global _restart_count, _last_exit_code
    process: subprocess.Popen[bytes] | None = None
    previous_snapshot = _snapshot()
    pending_change_at: float | None = None

    _log(f"Supervisor iniciado PID={os.getpid()} con Python {sys.executable}.")
    try:
        with BOT_LOG.open("ab", buffering=0) as bot_log:
            _clear_stale_polling_lock()
            process = _start_bot(bot_log)
            _write_status("running", process)
            while not _stop_requested:
                time.sleep(POLL_SECONDS)
                _write_status("running", process)

                current_snapshot = _snapshot()
                if current_snapshot != previous_snapshot:
                    previous_snapshot = current_snapshot
                    pending_change_at = time.monotonic()

                if pending_change_at is not None:
                    if time.monotonic() - pending_change_at >= DEBOUNCE_SECONDS:
                        valid, detail = _sources_compile()
                        if not valid:
                            _log(f"Cambio todavía no válido; se mantiene el bot actual. {detail}")
                            pending_change_at = time.monotonic()
                            continue
                        _log("Cambios válidos detectados; reiniciando el bot.")
                        _stop_bot(process)
                        time.sleep(1)
                        _restart_count += 1
                        _clear_stale_polling_lock()
                        process = _start_bot(bot_log)
                        _write_status("running", process)
                        pending_change_at = None
                        continue

                exit_code = process.poll() if process is not None else None
                if exit_code is not None and not _stop_requested:
                    _last_exit_code = int(exit_code)
                    _log(f"El bot terminó con código {exit_code}; reinicio automático en {RESTART_DELAY_SECONDS}s.")
                    _clear_stale_polling_lock()
                    time.sleep(RESTART_DELAY_SECONDS)
                    _restart_count += 1
                    _clear_stale_polling_lock()
                    process = _start_bot(bot_log)
                    _write_status("running", process)
    finally:
        _write_status("stopping", process)
        _stop_bot(process)
        _write_status("stopped", None)
        _release_supervisor_lock()
        _log("Supervisor detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
