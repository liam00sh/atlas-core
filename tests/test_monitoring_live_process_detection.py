from __future__ import annotations

import json

from monitoring.models import HealthState
from monitoring import supervisor as module


def test_pid_alive_uses_psutil_for_windows_processes(monkeypatch):
    class Process:
        def __init__(self, pid):
            assert pid == 123

        def is_running(self):
            return True

        def status(self):
            return "running"

    import psutil

    monkeypatch.setattr(psutil, "Process", Process)
    assert module._pid_alive(123)


def test_telegram_runtime_is_source_for_core_and_telegram(tmp_path, monkeypatch):
    status = tmp_path / "telegram_status.json"
    status.write_text(
        json.dumps(
            {
                "state": "running",
                "bot_pid": 22,
                "supervisor_pid": 11,
                "heartbeat": "2026-08-09T22:27:49",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TELEGRAM_STATUS_FILE", status)
    monkeypatch.setattr(module, "_pid_alive", lambda pid: pid in {11, 22})

    core = module._telegram_runtime_result("atlas_core", "Atlas Core")
    telegram = module._telegram_runtime_result("telegram", "Telegram")

    assert core.state is HealthState.OK
    assert telegram.state is HealthState.OK
    assert core.details["pid"] == 22
    assert core.recovery_action_id is None


def test_telegram_runtime_rejects_stale_or_dead_process(tmp_path, monkeypatch):
    status = tmp_path / "telegram_status.json"
    status.write_text(
        json.dumps({"state": "running", "bot_pid": 22, "supervisor_pid": 11}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TELEGRAM_STATUS_FILE", status)
    monkeypatch.setattr(module, "_pid_alive", lambda pid: pid == 11)

    result = module._telegram_runtime_result("telegram", "Telegram")

    assert result.state is HealthState.ERROR
    assert result.requires_intervention
    assert result.recovery_action_id == "service.telegram.restart"
