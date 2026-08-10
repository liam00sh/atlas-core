from __future__ import annotations

from types import SimpleNamespace

from monitoring.desktop_widgets import (
    DesktopWidgets,
    RASPBERRY_PANEL_TITLE,
    SERVICES_PANEL_TITLE,
)
from scripts import monitor_pc


def test_monitoring_panel_titles_match_latest_visual_contract() -> None:
    assert monitor_pc.PC_PANEL_TITLE == "ATLAS · ESTADO DEL PC"
    assert RASPBERRY_PANEL_TITLE == "ATLAS · ESTADO DE LA RPi"
    assert SERVICES_PANEL_TITLE == "ATLAS · SERVICIOS"


def test_pc_panel_keeps_additional_atlas_status_line(monkeypatch) -> None:
    monkeypatch.setattr(monitor_pc.psutil, "cpu_percent", lambda interval=None: 12.5)
    monkeypatch.setattr(
        monitor_pc.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=50.0, used=8 * 1024**3, total=16 * 1024**3),
    )
    monkeypatch.setattr(monitor_pc, "temperatures", lambda: "40 °C")
    monkeypatch.setattr(monitor_pc, "wifi_status", lambda: "90 %")
    monkeypatch.setattr(monitor_pc, "internet_status", lambda: "OK")
    monkeypatch.setattr(monitor_pc, "atlas_status", lambda: "OK")
    monkeypatch.setattr(monitor_pc, "uptime_status", lambda: "2 h")
    monkeypatch.setattr(monitor_pc, "process_count", lambda: 100)
    monkeypatch.setattr(monitor_pc, "load_status", lambda: "0.10 / 0.20 / 0.30")
    monkeypatch.setattr(monitor_pc, "gpu_status", lambda: {})
    monkeypatch.setattr(monitor_pc, "disk_lines", lambda: ["DISCO C:  50%"])

    rendered, _ = monitor_pc.snapshot()
    lines = rendered.splitlines()

    assert "ATLAS     OK" in lines
    assert lines.index("ATLAS     OK") == lines.index("INTERNET  OK") + 1
    assert lines.index("UPTIME    2 h") == lines.index("ATLAS     OK") + 1


def test_raspberry_and_services_render_as_separate_blocks() -> None:
    widget = DesktopWidgets.__new__(DesktopWidgets)
    payload = {
        "raspberry": {
            "state": "ok",
            "checked_at": "2026-08-10T09:30:00+02:00",
            "details": {
                "hostname": "atlas-core",
                "temperature_c": 72.0,
                "uptime_seconds": 7200,
                "network": {"primary_ip": "192.0.2.10"},
                "memory": {"used_bytes": 1024**3, "total_bytes": 4 * 1024**3},
                "sd": {"used_percent": 12.0, "free_bytes": 32 * 1024**3},
                "usb": {"mounted": True, "free_bytes": 100 * 1024**3},
                "docker": {"service_active": True},
                "home_assistant": {"container_running": True},
            },
        },
        "supervisor": {
            "checks": {
                "atlas_core": {"state": "ok"},
                "telegram": {"state": "ok"},
                "home_assistant": {"state": "ok"},
                "ollama": {"state": "ok"},
            }
        },
    }

    raspberry = widget._render_raspberry(payload)
    services = widget._render_services(payload)

    assert "SERVICIOS" not in raspberry
    assert "atlas_core         OK" in services
    assert "home_assistant     OK" in services
    assert "ollama             OK" in services
    assert "telegram           OK" in services


def test_services_renderer_keeps_legacy_payload_compatibility() -> None:
    widget = DesktopWidgets.__new__(DesktopWidgets)

    assert widget._render_services({"services": {"telegram": {"healthy": True}}}) == (
        "telegram           OK"
    )
