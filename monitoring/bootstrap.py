"""Construcción del supervisor desde variables de entorno y servicios existentes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from monitoring.desktop_state import DesktopStateWriter
from monitoring.incident_manager import IncidentManager
from monitoring.notification_router import NotificationRouter
from monitoring.raspberry_probe import RaspberryMonitor, RaspberryMonitorConfig
from monitoring.supervisor import AtlasSupervisor, SupervisorProbe


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on", "sí", "si"}


def _env_float(name: str, default: float, *, minimum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    if value != value or value in {float("inf"), float("-inf")}:
        return default
    return max(minimum, value)


def build_supervisor(
    *,
    telegram_sender: Callable[[str, str, str], bool],
    is_user_at_home: Callable[[str], bool] | None = None,
    has_capability: Callable[[str, str], bool] | None = None,
) -> tuple[AtlasSupervisor | None, RaspberryMonitor | None]:
    host = os.getenv("ATLAS_RASPBERRY_HOST", "").strip()
    user = os.getenv("ATLAS_RASPBERRY_USER", "atlas").strip()
    if not host:
        return None, None

    monitor = RaspberryMonitor(
        RaspberryMonitorConfig(
            host=host,
            user=user,
            ssh_port=int(os.getenv("ATLAS_RASPBERRY_SSH_PORT", "22")),
            timeout_seconds=_env_float(
                "ATLAS_RASPBERRY_TIMEOUT",
                6.0,
                minimum=0.1,
            ),
            sd_mount=os.getenv("ATLAS_RASPBERRY_SD_MOUNT", "/"),
            usb_mount=os.getenv("ATLAS_RASPBERRY_USB_MOUNT", "/mnt/atlas-storage"),
        )
    )

    router = NotificationRouter(
        send_private=telegram_sender,
        is_user_at_home=is_user_at_home,
        has_capability=has_capability,
    )

    incidents_path = Path(
        os.getenv(
            "ATLAS_INCIDENTS_PATH",
            "data/monitoring/incidents.json",
        )
    )
    manager = IncidentManager(
        incidents_path,
        on_opened=router.notify_opened,
        on_resolved=router.notify_resolved,
    )

    supervisor = AtlasSupervisor(
        probes=[
            SupervisorProbe(
                probe_id="raspberry",
                checker=monitor.collect,
            )
        ],
        incident_manager=manager,
        notification_router=router,
        state_writer=DesktopStateWriter(
            os.getenv(
                "ATLAS_SUPERVISOR_STATUS_PATH",
                "data/monitoring/supervisor_status.json",
            )
        ),
        interval_seconds=_env_float(
            "ATLAS_SUPERVISOR_INTERVAL",
            15.0,
            minimum=0.0,
        ),
    )
    return supervisor, monitor
