import sys
import types
from pathlib import Path

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
    """Usa una raíz temporal propia del proyecto en Windows.

    Evita que pytest intente mantener o limpiar el enlace global
    ``pytest-current`` dentro de ``%TEMP%``, que puede quedar bloqueado por
    antivirus, Google Drive, otra sesión de pytest o permisos del sistema.
    """

    if getattr(config.option, "basetemp", None):
        return

    project_root = Path(__file__).resolve().parent.parent
    base_temp = project_root / ".pytest_tmp"
    base_temp.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(base_temp)
