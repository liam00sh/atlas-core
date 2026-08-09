import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Stubs solo para poder probar el parche de forma aislada. En Atlas real se
# utilizan los módulos completos del proyecto.
if "core.log_manager" not in sys.modules:
    module = types.ModuleType("core.log_manager")
    module.write = lambda *args, **kwargs: None
    module.info = lambda *args, **kwargs: None
    module.warning = lambda *args, **kwargs: None
    module.error = lambda *args, **kwargs: None
    sys.modules["core.log_manager"] = module
if "memory.classifier" not in sys.modules:
    module = types.ModuleType("memory.classifier")
    module.classify_visibility = lambda content: ("private", "test")
    sys.modules["memory.classifier"] = module
if "memory.visibility" not in sys.modules:
    module = types.ModuleType("memory.visibility")

    module.PRIVATE = "private"
    module.ADMIN_MANAGED = "admin_managed"
    module.PARTNER = "partner"
    module.FAMILY = "family"
    module.KNOWN = "known"
    module.PUBLIC = "public"

    module.VISIBILITY_LABELS = {
        module.PRIVATE: "Solo el propietario",
        module.ADMIN_MANAGED: "Propietario y administrador",
        module.PARTNER: "Pareja autorizada",
        module.FAMILY: "Familia autorizada",
        module.KNOWN: "Personas de confianza",
        module.PUBLIC: "Cualquier persona",
    }

    module.VISIBILITY_OPTIONS = {
        "1": module.PRIVATE,
        "privado": module.PRIVATE,
        "privada": module.PRIVATE,
        "solo yo": module.PRIVATE,
        "2": module.ADMIN_MANAGED,
        "administrador": module.ADMIN_MANAGED,
        "gestion administrativa": module.ADMIN_MANAGED,
        "gestión administrativa": module.ADMIN_MANAGED,
        "3": module.PARTNER,
        "pareja": module.PARTNER,
        "4": module.FAMILY,
        "familia": module.FAMILY,
        "5": module.KNOWN,
        "confianza": module.KNOWN,
        "conocidos": module.KNOWN,
        "6": module.PUBLIC,
        "publico": module.PUBLIC,
        "público": module.PUBLIC,
        "cualquiera": module.PUBLIC,
    }

    def _normalize_visibility(value):
        if value is None:
            return None
        normalized = str(value).strip().casefold()
        if normalized in module.VISIBILITY_OPTIONS:
            return module.VISIBILITY_OPTIONS[normalized]
        if normalized in module.VISIBILITY_LABELS:
            return normalized
        return None

    module.normalize_visibility = _normalize_visibility
    sys.modules["memory.visibility"] = module


def pytest_configure(config):
    """Redirige toda persistencia de identidad y perfiles antes de recoger tests."""

    sandbox = tempfile.TemporaryDirectory(prefix="atlas-pytest-")
    sandbox_root = Path(sandbox.name)
    identity_data = sandbox_root / "identity"
    user_data = sandbox_root / "users"

    shutil.copytree(ROOT / "identity" / "data", identity_data)
    user_data.mkdir(parents=True, exist_ok=True)

    environment = {
        "ATLAS_IDENTITY_DATA_DIR": str(identity_data),
        "ATLAS_USER_DATA_DIR": str(user_data),
        "ATLAS_TELEGRAM_DATA_DIR": str(sandbox_root / "telegram"),
        "ATLAS_KNOWLEDGE_DATA_DIR": str(sandbox_root / "knowledge"),
        "ATLAS_INCIDENTS_PATH": str(sandbox_root / "monitoring" / "incidents.json"),
        "ATLAS_SUPERVISOR_STATUS_PATH": str(
            sandbox_root / "monitoring" / "supervisor_status.json"
        ),
    }
    previous_environment = {
        name: os.environ.get(name)
        for name in environment
    }
    os.environ.update(environment)

    config._atlas_persistence_sandbox = sandbox
    config._atlas_previous_environment = previous_environment


@pytest.fixture(autouse=True)
def isolate_persistent_data(tmp_path, monkeypatch):
    """Entrega a cada test una copia independiente de los datos persistentes."""

    identity_data = tmp_path / "identity"
    user_data = tmp_path / "users"
    monitoring_data = tmp_path / "monitoring"
    shutil.copytree(ROOT / "identity" / "data", identity_data)
    user_data.mkdir(parents=True, exist_ok=True)
    monitoring_data.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ATLAS_IDENTITY_DATA_DIR", str(identity_data))
    monkeypatch.setenv("ATLAS_USER_DATA_DIR", str(user_data))
    monkeypatch.setenv("ATLAS_TELEGRAM_DATA_DIR", str(tmp_path / "telegram"))
    monkeypatch.setenv("ATLAS_KNOWLEDGE_DATA_DIR", str(tmp_path / "knowledge"))
    monkeypatch.setenv(
        "ATLAS_INCIDENTS_PATH",
        str(monitoring_data / "incidents.json"),
    )
    monkeypatch.setenv(
        "ATLAS_SUPERVISOR_STATUS_PATH",
        str(monitoring_data / "supervisor_status.json"),
    )


def pytest_unconfigure(config):
    """Restaura solo el entorno del proceso y elimina el sandbox temporal."""

    previous_environment = getattr(
        config,
        "_atlas_previous_environment",
        {},
    )
    for name, previous_value in previous_environment.items():
        if previous_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous_value

    sandbox = getattr(config, "_atlas_persistence_sandbox", None)
    if sandbox is not None:
        sandbox.cleanup()
