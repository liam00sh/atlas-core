"""
Proyecto Atlas
Archivo: atlas_service_launcher.py

Gestor permanente de procesos técnicos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from monitoring.env_loader import load_monitoring_env


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_DIR = PROJECT_ROOT / "data" / "launcher"
LOG_DIR = PROJECT_ROOT / "logs" / "launcher"
LOCK_FILE = STATE_DIR / "atlas_service_launcher.lock"
STATUS_FILE = STATE_DIR / "service_launcher_status.json"
LOG_FILE = LOG_DIR / "atlas_service_launcher.log"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CREATE_NEW_PROCESS_GROUP = getattr(
    subprocess,
    "CREATE_NEW_PROCESS_GROUP",
    0,
)
POLL_SECONDS = 3.0
BACKOFF_SECONDS = (2, 5, 15, 30, 60)
RESTART_WINDOW_SECONDS = 900
MAX_RESTARTS = 8

_STOP = False


@dataclass
class ManagedProcess:
    name: str
    command: list[str]
    required_files: list[Path] = field(default_factory=list)
    required_modules: list[str] = field(default_factory=list)
    process: subprocess.Popen[bytes] | None = None
    restart_times: list[float] = field(default_factory=list)
    last_error: str | None = None
    last_start: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        for path in self.required_files:
            if not path.exists():
                errors.append(f"No existe: {path}")
        for module_name in self.required_modules:
            if importlib.util.find_spec(module_name) is None:
                errors.append(
                    f"No está disponible el módulo: {module_name}"
                )
        return errors

    def running(self) -> bool:
        return (
            self.process is not None
            and self.process.poll() is None
        )


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(f"{stamp} {message}\n")


def _python() -> Path:
    venv = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return venv
    return Path(sys.executable)


def _acquire_lock() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        try:
            payload = json.loads(
                LOCK_FILE.read_text(encoding="utf-8")
            )
            pid = int(payload.get("pid", 0))
        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            pid = 0

        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError:
                LOCK_FILE.unlink(missing_ok=True)
            else:
                raise RuntimeError(
                    "El launcher técnico ya está ejecutándose."
                )

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
    except Exception:
        pass


def _spawn(command: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(
            CREATE_NO_WINDOW
            | CREATE_NEW_PROCESS_GROUP
        ),
        env=os.environ.copy(),
    )


def _stop(*_args) -> None:
    global _STOP
    _STOP = True


def _write_status(
    processes: dict[str, ManagedProcess],
    environment_errors: list[str],
) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(
            {
                "launcher_pid": os.getpid(),
                "heartbeat": time.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "environment_ok": not environment_errors,
                "environment_errors": environment_errors,
                "processes": {
                    name: {
                        "running": item.running(),
                        "pid": (
                            item.process.pid
                            if item.running()
                            else None
                        ),
                        "restart_count": len(
                            item.restart_times
                        ),
                        "last_error": item.last_error,
                        "last_start": item.last_start,
                    }
                    for name, item in processes.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _build_processes() -> dict[str, ManagedProcess]:
    python = str(_python())
    return {
        "atlas_core": ManagedProcess(
            name="atlas_core",
            command=[
                python,
                str(PROJECT_ROOT / "main.py"),
                "--background",
            ],
            required_files=[PROJECT_ROOT / "main.py"],
        ),
        "telegram": ManagedProcess(
            name="telegram",
            command=[
                python,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "run_telegram_supervisor.py"
                ),
            ],
            required_files=[
                PROJECT_ROOT
                / "scripts"
                / "run_telegram_supervisor.py"
            ],
        ),
        "windows_lifecycle": ManagedProcess(
            name="windows_lifecycle",
            command=[
                python,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "windows_shutdown_listener.py"
                ),
            ],
            required_files=[
                PROJECT_ROOT
                / "scripts"
                / "windows_shutdown_listener.py"
            ],
        ),
        "system_supervisor": ManagedProcess(
            name="system_supervisor",
            command=[
                python,
                "-m",
                "monitoring.run_supervisor",
            ],
            required_files=[
                PROJECT_ROOT
                / "monitoring"
                / "run_supervisor.py"
            ],
            required_modules=["monitoring"],
        ),
    }


def main() -> int:
    if os.name != "nt":
        return 2

    load_monitoring_env()

    try:
        _acquire_lock()
    except RuntimeError as exc:
        _log(str(exc))
        return 11

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    processes = _build_processes()
    environment_errors: list[str] = []

    for item in processes.values():
        environment_errors.extend(
            f"{item.name}: {message}"
            for message in item.validate()
        )

    if environment_errors:
        for message in environment_errors:
            _log(message)

    _log("Launcher técnico iniciado.")

    try:
        while not _STOP:
            now = time.monotonic()

            for item in processes.values():
                if item.running():
                    continue

                item.restart_times = [
                    stamp
                    for stamp in item.restart_times
                    if now - stamp <= RESTART_WINDOW_SECONDS
                ]

                if len(item.restart_times) >= MAX_RESTARTS:
                    item.last_error = (
                        "Límite de reinicios alcanzado."
                    )
                    continue

                errors = item.validate()
                if errors:
                    item.last_error = "; ".join(errors)
                    continue

                delay = BACKOFF_SECONDS[
                    min(
                        len(item.restart_times),
                        len(BACKOFF_SECONDS) - 1,
                    )
                ]
                if item.restart_times:
                    time.sleep(delay)

                try:
                    item.process = _spawn(item.command)
                    item.restart_times.append(now)
                    item.last_start = time.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                    item.last_error = None
                    _log(
                        f"Iniciado {item.name} "
                        f"pid={item.process.pid}"
                    )
                except OSError as exc:
                    item.last_error = str(exc)
                    _log(
                        f"No se pudo iniciar "
                        f"{item.name}: {exc}"
                    )

            _write_status(processes, environment_errors)
            time.sleep(POLL_SECONDS)

    finally:
        for item in reversed(list(processes.values())):
            if not item.running():
                continue
            try:
                item.process.terminate()
            except OSError:
                pass

        _release_lock()
        _log("Launcher técnico detenido.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
