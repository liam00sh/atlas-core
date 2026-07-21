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
    module.info = lambda *args, **kwargs: None
    sys.modules["core.log_manager"] = module
if "memory.classifier" not in sys.modules:
    module = types.ModuleType("memory.classifier")
    module.classify_visibility = lambda content: ("private", "test")
    sys.modules["memory.classifier"] = module
if "memory.visibility" not in sys.modules:
    module = types.ModuleType("memory.visibility")
    module.normalize_visibility = lambda value: value
    module.VISIBILITY_LABELS = {"private": "Solo tú"}
    sys.modules["memory.visibility"] = module
