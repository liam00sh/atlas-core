import json
from dataclasses import asdict
from pathlib import Path

from monitoring.models import HealthCheckResult, HealthState


def test_health_check_result_serializable():
    health = HealthCheckResult(
        check_id="atlas_core",
        display_name="Atlas Core",
        state=HealthState.OK,
        available=True,
        details={"managed": True, "pid": 123},
    )
    payload = json.dumps(asdict(health))
    assert "atlas_core" in payload


def test_launcher_files_exist():
    assert Path("atlas_service_launcher.py").is_file()
    assert Path("atlas_desktop_launcher.py").is_file()
