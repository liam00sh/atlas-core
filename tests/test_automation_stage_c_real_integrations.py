import json
import zipfile
from pathlib import Path

from automation.automation_registry import AutomationRegistry
from automation.service_monitor import ServiceMonitor
from automation.stage_c_bootstrap import build_stage_c_environment
from automation.stage_c_integrations import (
    TelegramPrivateNotificationProvider,
    build_disk_probe,
    build_drive_probe,
    build_manual_project_backup_plan,
    build_ollama_probe,
    build_pc_status_probe,
    build_telegram_probe,
)


class FakeTelegram:
    def __init__(self):
        self.messages = []

    def get_me(self):
        return {"id": 42, "username": "atlas_bot"}

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))
        return {"ok": True}


class FakeOllama:
    model = "qwen"

    def is_available(self):
        return True


class FakeDrive:
    def health_check(self):
        return {"ok": True, "scope": "readonly"}


def test_real_telegram_probe_uses_get_me():
    monitor = ServiceMonitor()
    monitor.register(build_telegram_probe(FakeTelegram()))
    result = monitor.check("telegram")
    assert result["available"] is True
    assert result["details"]["username"] == "atlas_bot"


def test_real_ollama_probe_uses_is_available():
    monitor = ServiceMonitor()
    monitor.register(build_ollama_probe(FakeOllama()))
    result = monitor.check("ollama")
    assert result["available"] is True
    assert result["details"]["model"] == "qwen"


def test_drive_probe_prefers_health_check():
    monitor = ServiceMonitor()
    monitor.register(build_drive_probe(FakeDrive()))
    result = monitor.check("drive")
    assert result["available"] is True
    assert result["details"]["scope"] == "readonly"


def test_pc_status_probe_reads_published_monitor_file(tmp_path):
    status = tmp_path / "pc_status.json"
    status.write_text(
        json.dumps({"cpu_percent": 7.2, "ram_percent": 31.0}),
        encoding="utf-8",
    )
    monitor = ServiceMonitor()
    monitor.register(build_pc_status_probe(status, stale_after_seconds=600))
    result = monitor.check("pc_monitor")
    assert result["available"] is True
    assert result["details"]["status"]["cpu_percent"] == 7.2


def test_disk_probe_returns_real_values(tmp_path):
    monitor = ServiceMonitor()
    monitor.register(build_disk_probe(tmp_path, minimum_free_percent=0))
    result = monitor.check("disk")
    assert result["available"] is True
    assert result["details"]["total_bytes"] > 0


def test_manual_backup_plan_creates_verified_zip(tmp_path):
    project = tmp_path / "atlas_core"
    project.mkdir()
    (project / "main.py").write_text("print('atlas')", encoding="utf-8")
    (project / "__pycache__").mkdir()
    (project / "__pycache__" / "ignored.pyc").write_bytes(b"x")

    destination = tmp_path / "backups"
    plan = build_manual_project_backup_plan(
        project_root=project,
        destination_dir=destination,
    )
    result = plan.runner()

    archive = Path(result["archive"])
    assert result["verified"] is True
    assert archive.exists()
    with zipfile.ZipFile(archive) as handle:
        assert "main.py" in handle.namelist()
        assert not any("__pycache__" in item for item in handle.namelist())


def test_private_telegram_notification_uses_resolver():
    telegram = FakeTelegram()
    provider = TelegramPrivateNotificationProvider(
        telegram,
        lambda user_id: {"Alex": 123}.get(user_id),
    )
    assert provider.send("Alex", "Incidencia") is True
    assert telegram.messages == [(123, "Incidencia")]
    assert provider.send("Carla", "Incidencia") is False


def test_stage_c_environment_registers_real_catalog(tmp_path):
    project = tmp_path / "Atlas Project" / "04 - Python" / "atlas_core"
    project.mkdir(parents=True)
    (project / "main.py").write_text("", encoding="utf-8")
    data = project / "data"
    (data / "monitoring").mkdir(parents=True)
    (data / "monitoring" / "pc_status.json").write_text(
        json.dumps({"ok": True}),
        encoding="utf-8",
    )

    registry = AutomationRegistry()
    environment = build_stage_c_environment(
        registry=registry,
        project_root=project,
        data_root=data,
        telegram_client=FakeTelegram(),
        telegram_recipient_resolver=lambda user_id: 1,
        ollama_provider=FakeOllama(),
        drive_client=FakeDrive(),
        atlas_version_getter=lambda: "0.3.2-beta.1",
        atlas_started_getter=lambda: True,
    )

    assert registry.count == 5
    summary = environment.service_monitor.summary()
    ids = {item["service_id"] for item in summary["services"]}
    assert {"atlas", "disk", "pc_monitor", "telegram", "ollama", "drive"} <= ids
