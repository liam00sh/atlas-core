"""
===============================================================================
Proyecto Atlas
Archivo: atlas_launcher.py

Punto de entrada permanente y silencioso de Atlas en Windows.

Responsabilidades:
- Cargar el entorno.
- Evitar instancias duplicadas.
- Iniciar Atlas Core en modo background.
- Iniciar Telegram.
- Iniciar el supervisor técnico.
- Iniciar los widgets cuando existe sesión interactiva.
- Vigilar procesos y reiniciarlos con límites.
- Registrar estado y errores sin mostrar terminal.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Callable

from monitoring.env_loader import load_monitoring_env


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_DIR = PROJECT_ROOT / "data" / "launcher"
LOG_DIR = PROJECT_ROOT / "logs" / "launcher"
LOCK_FILE = STATE_DIR / "atlas_launcher.lock"
STATUS_FILE = STATE_DIR / "launcher_status.json"
LOG_FILE = LOG_DIR / "atlas_launcher.log"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)
CREATE_NEW_PROCESS_GROUP = getattr(
    subprocess,
    "CREATE_NEW_PROCESS_GROUP",
    0,
)

POLL_SECONDS = 5.0
MAX_RESTARTS = 5
RESTART_WINDOW_SECONDS = 900
BACKOFF_SECONDS = (2, 5, 15, 30, 60)

_stop_requested = False


@dataclass
class ManagedProcess:
    name: str
    command: list[str]
    interactive_only: bool = False
    required: bool = True
    process: subprocess.Popen[bytes] | None = None
    restart_times: list[float] = field(default_factory=list)
    last_exit_code: int | None = None
    disabled_until: float = 0.0

    def running(self) -> bool:
        return (
            self.process is not None
            and self.process.poll() is None
        )


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(f"{timestamp} {message}\n")


def _process_command_line(pid: int) -> str:
    if os.name != "nt" or pid <= 0:
        return ""

    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "$p = Get-CimInstance Win32_Process "
            f"-Filter \"ProcessId={pid}\"; "
            "if ($p) { $p.CommandLine }"
        ),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    return completed.stdout.strip()


def _pid_matches_launcher(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        command_line = _process_command_line(pid).casefold()
        return (
            "python" in command_line
            and "atlas_launcher.py" in command_line
        )

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _acquire_lock() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            payload = json.loads(
                LOCK_FILE.read_text(encoding="utf-8")
            )
            previous_pid = int(payload.get("pid", 0))
        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            previous_pid = 0

        if previous_pid and _pid_matches_launcher(previous_pid):
            raise RuntimeError(
                "Ya existe una instancia de atlas_launcher.py."
            )

        LOCK_FILE.unlink(missing_ok=True)

    descriptor = os.open(
        LOCK_FILE,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    try:
        os.write(
            descriptor,
            json.dumps({"pid": os.getpid()}).encode("utf-8"),
        )
    finally:
        os.close(descriptor)


def _release_lock() -> None:
    try:
        payload = json.loads(
            LOCK_FILE.read_text(encoding="utf-8")
        )
        if int(payload.get("pid", 0)) == os.getpid():
            LOCK_FILE.unlink(missing_ok=True)
    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        pass


def _interactive_session_available() -> bool:
    if os.name != "nt":
        return bool(os.environ.get("DISPLAY"))

    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                (
                    "(Get-Process explorer -ErrorAction "
                    "SilentlyContinue | Select-Object -First 1).Id"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return bool(completed.stdout.strip())


def _python_executable() -> Path:
    candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def _pythonw_executable() -> Path:
    candidate = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
    if candidate.is_file():
        return candidate

    current = Path(sys.executable)
    pythonw = current.with_name("pythonw.exe")
    if pythonw.is_file():
        return pythonw

    return current


def _spawn(item: ManagedProcess) -> None:
    executable = item.command[0]
    command = item.command

    flags = CREATE_NEW_PROCESS_GROUP
    if os.name == "nt":
        flags |= CREATE_NO_WINDOW

    item.process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        env=os.environ.copy(),
    )
    _log(f"Iniciado {item.name} pid={item.process.pid}")


def _trim_restarts(item: ManagedProcess, now: float) -> None:
    item.restart_times = [
        value
        for value in item.restart_times
        if now - value <= RESTART_WINDOW_SECONDS
    ]


def _restart_delay(item: ManagedProcess) -> float:
    index = min(
        len(item.restart_times),
        len(BACKOFF_SECONDS) - 1,
    )
    return float(BACKOFF_SECONDS[index])


def _write_status(processes: list[ManagedProcess]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "launcher_pid": os.getpid(),
        "heartbeat": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "interactive_session": _interactive_session_available(),
        "processes": {
            item.name: {
                "pid": (
                    item.process.pid
                    if item.running()
                    else None
                ),
                "running": item.running(),
                "last_exit_code": item.last_exit_code,
                "restart_count_window": len(item.restart_times),
                "disabled_until": item.disabled_until or None,
                "interactive_only": item.interactive_only,
            }
            for item in processes
        },
    }

    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATUS_FILE)


def _stop_children(processes: list[ManagedProcess]) -> None:
    for item in reversed(processes):
        process = item.process
        if process is None or process.poll() is not None:
            continue
        try:
            process.terminate()
        except OSError:
            continue

    deadline = time.monotonic() + 10
    for item in reversed(processes):
        process = item.process
        if process is None:
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            pass

    for item in reversed(processes):
        process = item.process
        if process is None or process.poll() is not None:
            continue
        try:
            process.kill()
        except OSError:
            pass


def _signal_handler(*_args) -> None:
    global _stop_requested
    _stop_requested = True


def _build_processes() -> list[ManagedProcess]:
    python = str(_python_executable())
    pythonw = str(_pythonw_executable())

    return [
        ManagedProcess(
            name="atlas_core",
            command=[
                python,
                str(PROJECT_ROOT / "main.py"),
                "--background",
            ],
        ),
        ManagedProcess(
            name="telegram",
            command=[
                python,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "run_telegram_supervisor.py"
                ),
            ],
        ),
        ManagedProcess(
            name="windows_lifecycle",
            command=[
                python,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "windows_shutdown_listener.py"
                ),
            ],
        ),
        ManagedProcess(
            name="monitor_pc",
            command=[
                pythonw,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "monitor_pc.py"
                ),
            ],
            interactive_only=True,
        ),
        ManagedProcess(
            name="monitor_rpi_banner",
            command=[
                pythonw,
                "-m",
                "monitoring.desktop_widgets",
            ],
            interactive_only=True,
        ),
        ManagedProcess(
            name="system_supervisor",
            command=[
                python,
                "-m",
                "monitoring.run_supervisor",
            ],
        ),
    ]


def main() -> int:
    if os.name != "nt":
        _log("atlas_launcher.py está preparado para Windows.")
        return 2

    load_monitoring_env()

    try:
        _acquire_lock()
    except RuntimeError as exc:
        _log(str(exc))
        return 11

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    processes = _build_processes()
    _log("Launcher iniciado.")

    try:
        while not _stop_requested:
            now = time.monotonic()
            interactive_available = (
                _interactive_session_available()
            )

            for item in processes:
                if item.running():
                    continue

                if item.process is not None:
                    item.last_exit_code = item.process.poll()
                    item.process = None

                if (
                    item.interactive_only
                    and not interactive_available
                ):
                    continue

                if item.disabled_until > now:
                    continue

                _trim_restarts(item, now)

                if len(item.restart_times) >= MAX_RESTARTS:
                    item.disabled_until = (
                        now + RESTART_WINDOW_SECONDS
                    )
                    _log(
                        f"{item.name} entra en enfriamiento "
                        f"durante {RESTART_WINDOW_SECONDS}s."
                    )
                    continue

                delay = _restart_delay(item)
                if item.restart_times:
                    time.sleep(delay)

                try:
                    _spawn(item)
                except OSError as exc:
                    item.last_exit_code = -1
                    item.restart_times.append(now)
                    _log(
                        f"No se pudo iniciar {item.name}: {exc}"
                    )
                    continue

                item.restart_times.append(now)

            _write_status(processes)
            time.sleep(POLL_SECONDS)

    finally:
        _log("Launcher deteniéndose.")
        _stop_children(processes)
        _release_lock()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
