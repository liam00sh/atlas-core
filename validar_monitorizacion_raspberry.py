from __future__ import annotations

import os
import sys

from monitoring.env_loader import load_monitoring_env
from monitoring.raspberry_probe import (
    RaspberryMonitor,
    RaspberryMonitorConfig,
)


def main() -> int:
    if not load_monitoring_env():
        print(
            "ERROR: falta la dependencia python-dotenv.\n"
            "Ejecuta: python -m pip install -r requirements.txt"
        )
        return 1

    host = os.getenv("ATLAS_RASPBERRY_HOST", "").strip()
    user = os.getenv("ATLAS_RASPBERRY_USER", "atlas").strip()

    if not host:
        print("ERROR: ATLAS_RASPBERRY_HOST no está configurado en .env")
        return 1

    monitor = RaspberryMonitor(
        RaspberryMonitorConfig(
            host=host,
            user=user,
            ssh_port=int(os.getenv("ATLAS_RASPBERRY_SSH_PORT", "22")),
            timeout_seconds=float(
                os.getenv("ATLAS_RASPBERRY_TIMEOUT", "6")
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

    result = monitor.collect()
    print(result)
    return 0 if result.available else 2


if __name__ == "__main__":
    raise SystemExit(main())
