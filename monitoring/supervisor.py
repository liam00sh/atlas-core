"""
Proyecto Atlas
Archivo: monitoring/supervisor.py

Supervisor completo de salud para Atlas.
Vigila:
- Atlas Core.
- Telegram.
- Monitor del PC.
- Monitor de Raspberry.
- Home Assistant.
- Ollama.

Los procesos locales controlados por los launchers pueden reiniciarse.
Los servicios externos solo se diagnostican y notifican.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Callable
from urllib import request, error

from monitoring.raspberry_probe import RaspberryMonitor, RaspberryMonitorConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_ROOT / "data" / "monitoring"
STATUS_FILE = STATE_DIR / "supervisor_status.json"
LAUNCHER_STATE_DIR = PROJECT_ROOT / "data" / "launcher"


@dataclass
class ServiceHealth:
    name: str
    healthy: bool
    managed: bool
    detail: str
    pid: int | None = None
    restart_requested: bool = False


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _check_launcher_process(
    launcher_file: Path,
    process_name: str,
    managed: bool = True,
) -> ServiceHealth:
    payload = _read_json(launcher_file)
    process = (
        payload.get("processes", {})
        .get(process_name, {})
    )
    pid = process.get("pid")
    running = bool(process.get("running")) and _pid_alive(pid)
    detail = "Proceso activo." if running else "Proceso detenido o sin estado."
    return ServiceHealth(
        name=process_name,
        healthy=running,
        managed=managed,
        detail=detail,
        pid=pid,
    )


def _http_health(
    name: str,
    url: str,
    timeout: float = 3.0,
) -> ServiceHealth:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=timeout) as response:
            code = int(response.status)
        healthy = 200 <= code < 500
        detail = f"HTTP {code}"
    except error.HTTPError as exc:
        healthy = 200 <= exc.code < 500
        detail = f"HTTP {exc.code}"
    except (error.URLError, TimeoutError, OSError) as exc:
        healthy = False
        detail = f"No accesible: {exc}"

    return ServiceHealth(
        name=name,
        healthy=healthy,
        managed=False,
        detail=detail,
    )


def _tcp_health(
    name: str,
    host: str,
    port: int,
    timeout: float = 2.0,
) -> ServiceHealth:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        healthy = True
        detail = f"TCP {host}:{port} accesible."
    except OSError as exc:
        healthy = False
        detail = f"TCP no accesible: {exc}"

    return ServiceHealth(
        name=name,
        healthy=healthy,
        managed=False,
        detail=detail,
    )


def _default_home_assistant_url() -> str:
    return os.getenv(
        "HOME_ASSISTANT_URL",
        os.getenv(
            "HA_URL",
            "http://192.168.1.31:8123",
        ),
    ).rstrip("/") + "/api/"


def _default_ollama_url() -> str:
    return os.getenv(
        "OLLAMA_URL",
        os.getenv(
            "OLLAMA_HOST",
            "http://127.0.0.1:11434",
        ),
    ).rstrip("/") + "/api/tags"


class AtlasSupervisor:
    def __init__(self) -> None:
        self.service_status = (
            LAUNCHER_STATE_DIR / "service_launcher_status.json"
        )
        self.desktop_status = (
            LAUNCHER_STATE_DIR / "desktop_launcher_status.json"
        )
        self.raspberry_monitor = RaspberryMonitor(
            RaspberryMonitorConfig(
                host=os.getenv(
                    "ATLAS_RASPBERRY_HOST",
                    "192.168.1.31",
                ),
                user=os.getenv(
                    "ATLAS_RASPBERRY_USER",
                    "atlas",
                ),
                ssh_port=int(
                    os.getenv(
                        "ATLAS_RASPBERRY_SSH_PORT",
                        "22",
                    )
                ),
                timeout_seconds=float(
                    os.getenv(
                        "ATLAS_RASPBERRY_TIMEOUT",
                        "6",
                    )
                ),
                sd_mount=os.getenv(
                    "ATLAS_RASPBERRY_SD_MOUNT",
                    "/",
                ),
                usb_mount=os.getenv(
                    "ATLAS_RASPBERRY_USB_MOUNT",
                    "/mnt/atlas-storage",
                ),
            )
        )

    def collect(self) -> list[ServiceHealth]:
        checks = [
            _check_launcher_process(
                self.service_status,
                "atlas_core",
            ),
            _check_launcher_process(
                self.service_status,
                "telegram",
            ),
            _check_launcher_process(
                self.desktop_status,
                "monitor_pc",
            ),
            _check_launcher_process(
                self.desktop_status,
                "desktop_widgets",
            ),
            _http_health(
                "home_assistant",
                _default_home_assistant_url(),
            ),
            _http_health(
                "ollama",
                _default_ollama_url(),
            ),
        ]

        return checks

    def write_status(
        self,
        checks: list[ServiceHealth],
        raspberry: dict,
    ) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        incidents: list[dict] = []

        for item in checks:
            if item.healthy:
                continue
            incidents.append(
                {
                    "severity": "critical",
                    "title": f"{item.name} no está disponible",
                    "message": item.detail,
                }
            )

        raspberry_state = str(
            raspberry.get("state", "unknown")
        ).casefold()
        if raspberry.get("available") is False or raspberry_state in {
            "critical",
            "error",
            "offline",
            "unavailable",
            "unknown",
            "",
        }:
            incidents.insert(
                0,
                {
                    "severity": "critical",
                    "title": "Problema en la Raspberry",
                    "message": raspberry.get("message")
                    or (
                        "No se puede obtener el estado de la Raspberry. "
                        "Puede estar apagada, sin red o sin acceso SSH."
                    ),
                },
            )
        elif raspberry_state == "warning":
            incidents.insert(
                0,
                {
                    "severity": "warning",
                    "title": "Aviso en la Raspberry",
                    "message": raspberry.get("message")
                    or "La Raspberry funciona con avisos.",
                },
            )

        healthy = (
            all(item.healthy for item in checks)
            and raspberry_state == "ok"
            and raspberry.get("available") is True
        )
        payload = {
            "heartbeat": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "healthy": healthy,
            "services": {
                item.name: asdict(item)
                for item in checks
            },
            "raspberry": raspberry,
            "incidents": incidents,
        }
        STATUS_FILE.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def run_once(self) -> list[ServiceHealth]:
        checks = self.collect()
        raspberry_result = self.raspberry_monitor.collect()
        raspberry = {
            "check_id": raspberry_result.check_id,
            "display_name": raspberry_result.display_name,
            "state": raspberry_result.state.value,
            "available": raspberry_result.available,
            "message": raspberry_result.message,
            "error_code": raspberry_result.error_code,
            "details": raspberry_result.details,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.write_status(checks, raspberry)
        return checks
