"""
Proyecto Atlas
Archivo: atlas_desktop_launcher.py

Gestor permanente de procesos gráficos.
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


PROJECT_ROOT = Path(__file__).resolve().parent
STATE_DIR = PROJECT_ROOT / "data" / "launcher"
LOG_DIR = PROJECT_ROOT / "logs" / "launcher"
LOCK_FILE = STATE_DIR / "atlas_desktop_launcher.lock"
STATUS_FILE = STATE_DIR / "desktop_launcher_status.json"
LOG_FILE = LOG_DIR / "atlas_desktop_launcher.log"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CREATE_NEW_PROCESS_GROUP = getattr(
    subprocess,
    "CREATE_NEW_PROCESS_GROUP",
    0,
)
BACKOFF_SECONDS = (2, 5, 15, 30, 60)
POLL_SECONDS = 3.0
_STOP = False


@dataclass
class ManagedProcess:
    name: str
    command: list[str]
    required_files: list[Path] = field(default_factory=list)
    process: subprocess.Popen[bytes] | None = None
    restart_count: int = 0
    last_error: str | None = None

    def running(self) -> bool:
        return (
            self.process is not None
            and self.process.poll() is None
        )


def _pythonw() -> Path:
    candidate = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
    if candidate.is_file():
        return candidate

    current = Path(sys.executable)
    candidate = current.with_name("pythonw.exe")
    if candidate.is_file():
        return candidate
    return current


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(
            f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
            f"{message}\n"
        )


def _acquire_lock() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            payload = json.loads(
                LOCK_FILE.read_text(encoding="utf-8")
            )
            pid = int(payload.get("pid", 0))
            os.kill(pid, 0)
        except Exception:
            LOCK_FILE.unlink(missing_ok=True)
        else:
            raise RuntimeError(
                "El launcher gráfico ya está ejecutándose."
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
    LOCK_FILE.unlink(missing_ok=True)


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


def main() -> int:
    if os.name != "nt":
        return 2

    try:
        _acquire_lock()
    except RuntimeError as exc:
        _log(str(exc))
        return 11

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    pythonw = str(_pythonw())
    processes = {
        "monitor_pc": ManagedProcess(
            name="monitor_pc",
            command=[
                pythonw,
                str(
                    PROJECT_ROOT
                    / "scripts"
                    / "monitor_pc.py"
                ),
            ],
            required_files=[
                PROJECT_ROOT
                / "scripts"
                / "monitor_pc.py"
            ],
        ),
        "desktop_widgets": ManagedProcess(
            name="desktop_widgets",
            command=[
                pythonw,
                "-m",
                "monitoring.desktop_widgets",
            ],
            required_files=[
                PROJECT_ROOT
                / "monitoring"
                / "desktop_widgets.py"
            ],
        ),
    }

    try:
        while not _STOP:
            for item in processes.values():
                if item.running():
                    continue

                missing = [
                    str(path)
                    for path in item.required_files
                    if not path.exists()
                ]
                if missing:
                    item.last_error = (
                        "No existe: " + ", ".join(missing)
                    )
                    continue

                delay = BACKOFF_SECONDS[
                    min(
                        item.restart_count,
                        len(BACKOFF_SECONDS) - 1,
                    )
                ]
                if item.restart_count:
                    time.sleep(delay)

                try:
                    item.process = _spawn(item.command)
                    item.restart_count += 1
                    item.last_error = None
                    _log(
                        f"Iniciado {item.name} "
                        f"pid={item.process.pid}"
                    )
                except OSError as exc:
                    item.last_error = str(exc)

            STATE_DIR.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(
                json.dumps(
                    {
                        "launcher_pid": os.getpid(),
                        "heartbeat": time.strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        ),
                        "processes": {
                            name: {
                                "running": item.running(),
                                "pid": (
                                    item.process.pid
                                    if item.running()
                                    else None
                                ),
                                "restart_count": (
                                    item.restart_count
                                ),
                                "last_error": item.last_error,
                            }
                            for name, item in processes.items()
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            time.sleep(POLL_SECONDS)

    finally:
        for item in reversed(list(processes.values())):
            if item.running():
                try:
                    item.process.terminate()
                except OSError:
                    pass

        _release_lock()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
