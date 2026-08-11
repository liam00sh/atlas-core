from conversation.daxter_personality import (
    PersonalityAdapter,
    PersonalityStrength,
    ResponseStyleContext,
)


def test_factual_content_is_preserved_verbatim():
    base = "La temperatura es 21 grados y la luz sigue apagada."
    result = PersonalityAdapter().adapt(base, ResponseStyleContext(request_type="general"), seed=7)
    assert base in result.styled_text


def test_serious_and_emergency_modes_are_plain():
    adapter = PersonalityAdapter()
    base = "Llama al 112 y aléjate del humo."
    emergency = adapter.adapt(base, ResponseStyleContext(request_type="emergency", personality_strength=PersonalityStrength.HIGH))
    assert emergency.styled_text == base
    assert emergency.personality_strength_used == PersonalityStrength.LOW
    private = adapter.adapt("No tienes permiso para ver esos datos.", ResponseStyleContext(request_type="privacy"))
    assert private.styled_text == "No tienes permiso para ver esos datos."


def test_low_normal_high_and_seed_are_deterministic():
    adapter = PersonalityAdapter()
    base = "La acción terminó correctamente."
    low = adapter.adapt(base, ResponseStyleContext(personality_strength=PersonalityStrength.LOW), seed=4)
    normal = adapter.adapt(base, ResponseStyleContext(request_type="success"), seed=4)
    high_context = ResponseStyleContext(request_type="success", personality_strength=PersonalityStrength.HIGH)
    high = adapter.adapt(base, high_context, seed=4)
    assert low.styled_text == base
    assert normal.styled_text != base
    assert len(high.styled_text) > len(normal.styled_text)
    assert high == adapter.adapt(base, high_context, seed=4)


def test_driving_is_brief_and_personality_is_separate_from_tts():
    result = PersonalityAdapter().adapt(
        "Gira a la derecha dentro de cien metros.",
        ResponseStyleContext(request_type="driving", personality_strength=PersonalityStrength.HIGH),
    )
    assert result.styled_text == "Gira a la derecha dentro de cien metros."
    assert not hasattr(result, "cfg_weight")
