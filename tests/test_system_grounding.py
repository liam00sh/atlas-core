from types import SimpleNamespace

from core.system_grounding import grounded_docker_status


def test_docker_status_reports_real_server_version(monkeypatch):
    monkeypatch.setattr("core.system_grounding.shutil.which", lambda _name: "docker")
    monkeypatch.setattr(
        "core.system_grounding.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="27.5.1\n"),
    )
    response = grounded_docker_status()
    assert "27.5.1" in response
    assert "consultado" in response


def test_docker_status_never_invents_availability(monkeypatch):
    monkeypatch.setattr("core.system_grounding.shutil.which", lambda _name: None)
    assert "No puedo comprobar" in grounded_docker_status()
