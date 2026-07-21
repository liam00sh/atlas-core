from core.atlas_daily_brief import _norm
from telegram_interface.lifecycle import _key


def test_daily_brief_normalization():
    assert _norm("¡Buenos días!") == "¡buenos dias!"


def test_lifecycle_personality_key():
    assert _key("Daxter") == "daxter"
    assert _key("Coco") == "coco"
    assert _key("otro") == "atlas"
