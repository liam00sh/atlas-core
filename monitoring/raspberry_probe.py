"""Monitorización remota y de solo lectura de la Raspberry Pi de Atlas."""

from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import subprocess
from typing import Callable

from monitoring.models import HealthCheckResult, HealthState


@dataclass(slots=True, frozen=True)
class RaspberryMonitorConfig:
    host: str
    user: str
    ssh_port: int = 22
    timeout_seconds: float = 6.0
    sd_mount: str = "/"
    usb_mount: str = "/mnt/atlas-storage"
    home_assistant_url: str | None = None


class RaspberryMonitor:
    """Recoge métricas importantes sin modificar la Raspberry."""

    def __init__(
        self,
        config: RaspberryMonitorConfig,
        *,
        command_runner: Callable[[list[str], float], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.config = config
        self._command_runner = command_runner or self._default_runner

    @staticmethod
    def _default_runner(
        command: list[str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8",
            errors="replace",
        )

    def _tcp_available(self) -> bool:
        try:
            with socket.create_connection(
                (self.config.host, self.config.ssh_port),
                timeout=self.config.timeout_seconds,
            ):
                return True
        except OSError:
            return False

    def _ssh(self, remote_command: str) -> subprocess.CompletedProcess[str]:
        command = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={int(self.config.timeout_seconds)}",
            "-o", "StrictHostKeyChecking=accept-new",
            "-p", str(self.config.ssh_port),
            f"{self.config.user}@{self.config.host}",
            remote_command,
        ]
        return self._command_runner(command, self.config.timeout_seconds + 2)

    @staticmethod
    def _shell_script(config: RaspberryMonitorConfig) -> str:
        sd_mount = json.dumps(config.sd_mount)
        usb_mount = json.dumps(config.usb_mount)
        return f"""
set -eu
python3 - <<'PY'
import json, os, shutil, subprocess, time

def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def disk(path):
    try:
        usage = shutil.disk_usage(path)
        return {{
            "mount": path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0.0,
            "mounted": os.path.ismount(path),
        }}
    except Exception:
        return {{
            "mount": path,
            "mounted": False,
            "error": "unavailable",
        }}

temp_raw = run(["bash", "-lc", "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || true"])
temperature_c = None
try:
    temperature_c = round(float(temp_raw) / 1000.0, 1)
except Exception:
    pass

load1 = load5 = load15 = None
try:
    load1, load5, load15 = [round(v, 2) for v in os.getloadavg()]
except Exception:
    pass

mem = {{}}
try:
    values = {{}}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    mem = {{
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": max(total - available, 0),
        "used_percent": round(((total - available) / total) * 100, 2) if total else 0.0,
    }}
except Exception:
    pass

docker_active = run(["bash", "-lc", "systemctl is-active docker 2>/dev/null || true"])
docker_info = run(["bash", "-lc", "docker info --format '{{{{json .ServerVersion}}}}' 2>/dev/null || true"])
containers_raw = run(["bash", "-lc", "docker ps --format '{{{{.Names}}}}|{{{{.Status}}}}|{{{{.Image}}}}' 2>/dev/null || true"])
containers = []
for line in containers_raw.splitlines():
    parts = line.split("|", 2)
    if len(parts) == 3:
        containers.append({{"name": parts[0], "status": parts[1], "image": parts[2]}})

ha_running = any(item["name"] == "homeassistant" for item in containers)

payload = {{
    "hostname": run(["hostname"]),
    "kernel": run(["uname", "-r"]),
    "uptime_seconds": float(run(["bash", "-lc", "cut -d. -f1 /proc/uptime"]) or 0),
    "temperature_c": temperature_c,
    "load": {{"1m": load1, "5m": load5, "15m": load15}},
    "memory": mem,
    "sd": disk({sd_mount}),
    "usb": disk({usb_mount}),
    "docker": {{
        "service_active": docker_active == "active",
        "server_version": docker_info.strip('"') if docker_info else None,
        "containers": containers,
    }},
    "home_assistant": {{
        "container_running": ha_running,
    }},
    "network": {{
        "primary_ip": run(["bash", "-lc", "hostname -I | awk '{{print $1}}'"]),
    }},
}}
print(json.dumps(payload, ensure_ascii=False))
PY
""".strip()

    def collect(self) -> HealthCheckResult:
        if not self._tcp_available():
            return HealthCheckResult(
                check_id="raspberry",
                display_name="Raspberry Pi",
                state=HealthState.CRITICAL,
                available=False,
                message="La Raspberry no responde por SSH.",
                error_code="ssh_unavailable",
            )

        result = self._ssh(self._shell_script(self.config))
        if result.returncode != 0:
            return HealthCheckResult(
                check_id="raspberry",
                display_name="Raspberry Pi",
                state=HealthState.ERROR,
                available=False,
                message="No se pudieron obtener las métricas de la Raspberry.",
                error_code="ssh_command_failed",
                details={"stderr": result.stderr[-300:]},
            )

        try:
            details = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return HealthCheckResult(
                check_id="raspberry",
                display_name="Raspberry Pi",
                state=HealthState.ERROR,
                available=False,
                message="La Raspberry devolvió una respuesta no válida.",
                error_code="invalid_json",
            )

        warnings: list[str] = []
        critical: list[str] = []

        temperature = details.get("temperature_c")
        if isinstance(temperature, (int, float)):
            if temperature >= 80:
                critical.append("temperature")
            elif temperature >= 75:
                warnings.append("temperature")

        sd = details.get("sd", {})
        if not sd.get("mounted", False):
            critical.append("sd")
        elif float(sd.get("used_percent", 0)) >= 90:
            critical.append("sd_space")
        elif float(sd.get("used_percent", 0)) >= 80:
            warnings.append("sd_space")

        usb = details.get("usb", {})
        if self.config.usb_mount and not usb.get("mounted", False):
            warnings.append("usb_mount")
        elif float(usb.get("used_percent", 0)) >= 90:
            critical.append("usb_space")
        elif float(usb.get("used_percent", 0)) >= 80:
            warnings.append("usb_space")

        docker = details.get("docker", {})
        if not docker.get("service_active", False):
            critical.append("docker")

        home_assistant = details.get("home_assistant", {})
        if not home_assistant.get("container_running", False):
            critical.append("home_assistant")

        memory = details.get("memory", {})
        memory_percent = float(memory.get("used_percent", 0))
        if memory_percent >= 95:
            critical.append("memory")
        elif memory_percent >= 85:
            warnings.append("memory")

        details["warnings"] = warnings
        details["critical"] = critical

        if critical:
            state = HealthState.CRITICAL
            available = False
            message = "Se han detectado problemas críticos en la Raspberry."
        elif warnings:
            state = HealthState.WARNING
            available = True
            message = "La Raspberry funciona con avisos."
        else:
            state = HealthState.OK
            available = True
            message = "La Raspberry funciona correctamente."

        return HealthCheckResult(
            check_id="raspberry",
            display_name="Raspberry Pi",
            state=state,
            available=available,
            details=details,
            message=message,
        )
