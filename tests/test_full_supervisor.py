import json
from pathlib import Path

from monitoring.supervisor import ServiceHealth


def test_service_health_serializable():
    health = ServiceHealth(
        name="atlas_core",
        healthy=True,
        managed=True,
        detail="ok",
        pid=123,
    )
    payload = json.dumps(health.__dict__)
    assert "atlas_core" in payload


def test_launcher_files_exist():
    assert Path("atlas_service_launcher.py").is_file()
    assert Path("atlas_desktop_launcher.py").is_file()
