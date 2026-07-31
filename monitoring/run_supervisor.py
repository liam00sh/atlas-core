"""
Proyecto Atlas
Archivo: monitoring/run_supervisor.py
"""

from __future__ import annotations

import signal
from monitoring.env_loader import load_monitoring_env
from monitoring.supervisor import AtlasSupervisor


_STOP = False


def _stop(*_args) -> None:
    global _STOP
    _STOP = True


def main() -> int:
    load_monitoring_env()
    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    supervisor = AtlasSupervisor()
    try:
        while not _STOP:
            supervisor.run_once()
            if supervisor.wait(supervisor.interval_seconds):
                break
    finally:
        supervisor.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
