import sys
import types

log_manager = types.ModuleType("core.log_manager")
log_manager.info = lambda *_args, **_kwargs: None
sys.modules.setdefault("core.log_manager", log_manager)
classifier = types.ModuleType("memory.classifier")
classifier.classify_visibility = lambda _content: (None, "test")
sys.modules.setdefault("memory.classifier", classifier)
visibility = types.ModuleType("memory.visibility")
visibility.normalize_visibility = lambda value: value
visibility.VISIBILITY_LABELS = {}
sys.modules.setdefault("memory.visibility", visibility)

from core.atlas_humor import AtlasHumorMixin
from memory.memory_service import MemoryService
from telegram_interface.progress import progress_delay_for


def test_humor_categories_are_specific_and_safe():
    assert AtlasHumorMixin._humor_category("Cuéntame un chiste de informáticos") == "informatica"
    assert AtlasHumorMixin._humor_category("Cuéntame un chiste de bomberos") == "bomberos"
    assert AtlasHumorMixin._humor_category("Cuéntame un chiste machista") == "prejuicios"


def test_memories_use_second_person():
    convert = MemoryService._memory_in_second_person
    assert convert("mi coche es un Hyundai", self_view=True) == "Tu coche es un Hyundai"
    assert convert("trabajo como administrador", self_view=True) == "Trabajas como administrador"
    assert convert("me gusta cocinar", self_view=True) == "Te gusta cocinar"


def test_internet_progress_is_immediate():
    assert progress_delay_for("Busca en internet habitantes de Alicante") == 0.0
    assert 0 < progress_delay_for("Qué sabes sobre mí") <= 0.7
