"""Supervisor unificado de salud para Atlas.

Todas las sondas producen :class:`HealthCheckResult`. Los fallos se aíslan por
sonda, se convierten en resultados controlados y se procesan mediante el gestor
de incidencias, el enrutador de notificaciones y el escritor de estado comunes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import logging
import os
from pathlib import Path
import socket
from threading import Event
import time
from typing import Callable
from urllib import error, request

from monitoring.desktop_state import DesktopStateWriter
from monitoring.incident_manager import IncidentManager
from monitoring.models import HealthCheckResult, HealthState
from monitoring.notification_router import NotificationRouter
from monitoring.raspberry_probe import RaspberryMonitor, RaspberryMonitorConfig


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_ROOT / "data" / "monitoring"
STATUS_FILE = STATE_DIR / "supervisor_status.json"
LAUNCHER_STATE_DIR = PROJECT_ROOT / "data" / "launcher"


@dataclass(slots=True, frozen=True)
class SupervisorProbe:
    """Sonda de salud inyectable identificada de forma estable."""

    probe_id: str
    checker: Callable[[], HealthCheckResult]

    def __post_init__(self) -> None:
        if not self.probe_id.strip():
            raise ValueError("probe_id no puede estar vacío")
        if not callable(self.checker):
            raise TypeError("checker debe ser invocable")


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


def _launcher_process_result(
    launcher_file: Path,
    process_name: str,
    *,
    managed: bool = True,
) -> HealthCheckResult:
    process = _read_json(launcher_file).get("processes", {}).get(
        process_name,
        {},
    )
    pid = process.get("pid")
    running = bool(process.get("running")) and _pid_alive(pid)
    return HealthCheckResult(
        check_id=process_name,
        display_name=process_name.replace("_", " ").title(),
        state=HealthState.OK if running else HealthState.ERROR,
        available=running,
        message=(
            "Proceso activo."
            if running
            else "Proceso detenido o sin estado."
        ),
        details={"managed": managed, "pid": pid},
    )


def _http_health_result(
    check_id: str,
    display_name: str,
    url: str,
    *,
    timeout: float = 3.0,
) -> HealthCheckResult:
    try:
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=max(0.1, timeout)) as response:
            code = int(response.status)
        available = 200 <= code < 500
        message = f"HTTP {code}"
    except error.HTTPError as exc:
        available = 200 <= exc.code < 500
        message = f"HTTP {exc.code}"
    except (error.URLError, TimeoutError, OSError) as exc:
        available = False
        message = f"No accesible ({type(exc).__name__})."

    return HealthCheckResult(
        check_id=check_id,
        display_name=display_name,
        state=HealthState.OK if available else HealthState.ERROR,
        available=available,
        message=message,
    )


def _tcp_health_result(
    check_id: str,
    display_name: str,
    host: str,
    port: int,
    *,
    timeout: float = 2.0,
) -> HealthCheckResult:
    try:
        with socket.create_connection(
            (host, port),
            timeout=max(0.1, timeout),
        ):
            pass
        available = True
        message = f"TCP {host}:{port} accesible."
    except OSError as exc:
        available = False
        message = f"TCP no accesible ({type(exc).__name__})."

    return HealthCheckResult(
        check_id=check_id,
        display_name=display_name,
        state=HealthState.OK if available else HealthState.ERROR,
        available=available,
        message=message,
    )


def _default_home_assistant_url() -> str:
    return os.getenv(
        "HOME_ASSISTANT_URL",
        os.getenv("HA_URL", "http://192.168.1.31:8123"),
    ).rstrip("/") + "/api/"


def _default_ollama_url() -> str:
    return os.getenv(
        "OLLAMA_URL",
        os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
    ).rstrip("/") + "/api/tags"


def _finite_float(
    value: str | float | int,
    *,
    default: float,
    minimum: float,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return default
    return max(minimum, parsed)


class AtlasSupervisor:
    """Coordina sondas, incidencias, avisos y estado persistente."""

    def __init__(
        self,
        *,
        probes: list[SupervisorProbe] | None = None,
        incident_manager: IncidentManager | None = None,
        notification_router: NotificationRouter | None = None,
        state_writer: DesktopStateWriter | None = None,
        interval_seconds: float = 10.0,
    ) -> None:
        self.interval_seconds = _finite_float(
            interval_seconds,
            default=10.0,
            minimum=0.0,
        )
        self.service_status = (
            LAUNCHER_STATE_DIR / "service_launcher_status.json"
        )
        self.desktop_status = (
            LAUNCHER_STATE_DIR / "desktop_launcher_status.json"
        )
        self.raspberry_monitor = RaspberryMonitor(
            RaspberryMonitorConfig(
                host=os.getenv("ATLAS_RASPBERRY_HOST", "192.168.1.31"),
                user=os.getenv("ATLAS_RASPBERRY_USER", "atlas"),
                ssh_port=int(os.getenv("ATLAS_RASPBERRY_SSH_PORT", "22")),
                timeout_seconds=_finite_float(
                    os.getenv("ATLAS_RASPBERRY_TIMEOUT", "6"),
                    default=6.0,
                    minimum=0.1,
                ),
                sd_mount=os.getenv("ATLAS_RASPBERRY_SD_MOUNT", "/"),
                usb_mount=os.getenv(
                    "ATLAS_RASPBERRY_USB_MOUNT",
                    "/mnt/atlas-storage",
                ),
            )
        )
        self.notification_router = notification_router or NotificationRouter(
            send_private=lambda *_args: False,
        )
        self.incident_manager = incident_manager or IncidentManager(
            STATE_DIR / "incidents.json",
        )
        if self.incident_manager.on_opened is None:
            self.incident_manager.on_opened = (
                self.notification_router.notify_opened
            )
        if self.incident_manager.on_resolved is None:
            self.incident_manager.on_resolved = (
                self.notification_router.notify_resolved
            )
        self.state_writer = state_writer or DesktopStateWriter(STATUS_FILE)
        self.probes = (
            list(probes)
            if probes is not None
            else self._default_probes()
        )
        self._stop_event = Event()
        self._closed = False

    def _default_probes(self) -> list[SupervisorProbe]:
        http_timeout = _finite_float(
            os.getenv("ATLAS_HTTP_PROBE_TIMEOUT", "3"),
            default=3.0,
            minimum=0.1,
        )
        return [
            SupervisorProbe(
                "atlas_core",
                lambda: _launcher_process_result(
                    self.service_status,
                    "atlas_core",
                ),
            ),
            SupervisorProbe(
                "telegram",
                lambda: _launcher_process_result(
                    self.service_status,
                    "telegram",
                ),
            ),
            SupervisorProbe(
                "monitor_pc",
                lambda: _launcher_process_result(
                    self.desktop_status,
                    "monitor_pc",
                ),
            ),
            SupervisorProbe(
                "desktop_widgets",
                lambda: _launcher_process_result(
                    self.desktop_status,
                    "desktop_widgets",
                ),
            ),
            SupervisorProbe(
                "home_assistant",
                lambda: _http_health_result(
                    "home_assistant",
                    "Home Assistant",
                    _default_home_assistant_url(),
                    timeout=http_timeout,
                ),
            ),
            SupervisorProbe(
                "ollama",
                lambda: _http_health_result(
                    "ollama",
                    "Ollama",
                    _default_ollama_url(),
                    timeout=http_timeout,
                ),
            ),
            SupervisorProbe("raspberry", self.raspberry_monitor.collect),
        ]

    @staticmethod
    def _probe_failure(
        probe: SupervisorProbe,
        exc: Exception,
    ) -> HealthCheckResult:
        error_type = type(exc).__name__
        LOGGER.error(
            "La sonda %s ha fallado (%s).",
            probe.probe_id,
            error_type,
        )
        return HealthCheckResult(
            check_id=probe.probe_id,
            display_name=probe.probe_id.replace("_", " ").title(),
            state=HealthState.ERROR,
            available=False,
            error_code="probe_exception",
            message=f"Fallo interno de la sonda ({error_type}).",
        )

    def collect(self) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for probe in self.probes:
            try:
                result = probe.checker()
                if not isinstance(result, HealthCheckResult):
                    raise TypeError("checker debe devolver HealthCheckResult")
                if result.check_id != probe.probe_id:
                    LOGGER.warning(
                        "La sonda %s devolvió un identificador diferente.",
                        probe.probe_id,
                    )
                    result = replace(result, check_id=probe.probe_id)
            except Exception as exc:
                result = self._probe_failure(probe, exc)
            results.append(result)
        return results

    def run_once(self) -> list[HealthCheckResult]:
        if self._closed:
            raise RuntimeError("El supervisor está cerrado.")

        results = self.collect()
        for result in results:
            affected_users = self.notification_router.affected_users_for(
                result.check_id
            )
            self.incident_manager.apply_result(
                result,
                affected_users=affected_users,
            )

        raspberry = next(
            (result for result in results if result.check_id == "raspberry"),
            None,
        )
        self.state_writer.write(
            raspberry=raspberry,
            active_incidents=self.incident_manager.active_incidents(),
            supervisor={
                "heartbeat": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "healthy": all(result.available for result in results),
                "interval_seconds": self.interval_seconds,
                "checks": {
                    result.check_id: asdict(result)
                    for result in results
                },
            },
        )
        return results

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.interval_seconds)

    def wait(self, timeout: float | None = None) -> bool:
        """Espera una parada; permite ciclos interrumpibles sin sondeo activo."""

        return self._stop_event.wait(timeout)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Solicita la parada y evita que se inicien ciclos nuevos."""

        self._stop_event.set()
        self._closed = True

    def __enter__(self) -> AtlasSupervisor:
        return self

    def __exit__(self, *_args) -> None:
        self.close()
