import pytest

from ai.models.roles import ModelRole
from ai.prompts.system_prompt import BASE_SYSTEM_PROMPT
from ai.routing.router import AIRouter, RoutingRequest
from core.atlas_ai import AtlasAIMixin
from telegram_interface.response_modes import (
    TelegramResponseMode,
    detect_response_mode_directive,
    is_response_mode_status_query,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("modo texto", TelegramResponseMode.TEXT_ONLY),
        ("solo texto", TelegramResponseMode.TEXT_ONLY),
        ("responde solo por texto", TelegramResponseMode.TEXT_ONLY),
        ("responde solo en modo texto", TelegramResponseMode.TEXT_ONLY),
        ("cambia a modo texto", TelegramResponseMode.TEXT_ONLY),
        ("desactiva la voz", TelegramResponseMode.TEXT_ONLY),
        ("no hables", TelegramResponseMode.TEXT_ONLY),
        ("modo voz", TelegramResponseMode.AUDIO_ONLY),
        ("activa la voz", TelegramResponseMode.AUDIO_ONLY),
        ("vuelve a hablar", TelegramResponseMode.AUDIO_ONLY),
        ("texto y voz", TelegramResponseMode.AUTOMATIC),
    ],
)
def test_natural_voice_mode_controls_are_deterministic(text, expected) -> None:
    assert detect_response_mode_directive(text) is expected


def test_voice_status_is_a_query_not_a_mode_change() -> None:
    assert is_response_mode_status_query("estado voz")
    assert detect_response_mode_directive("estado voz") is None


def test_previous_turn_intent_routes_to_reasoning() -> None:
    decision = AIRouter().route(
        RoutingRequest(
            message="¿Por qué crees que te acabo de decir eso?",
            context_messages=2,
            memory_required=True,
        )
    )
    assert decision.role is ModelRole.REASONING
    assert "context" in decision.reasons


def test_short_sentence_request_is_enforced_even_if_fast_model_rambles() -> None:
    response = AtlasAIMixin._apply_literal_response_constraints(
        "Dime una frase corta sobre el acuario",
        "¡Ey Alex, venga! El acuario pequeño parece un rincón tranquilo de casa. Después viví una aventura larguísima con peces dorados.",
    )
    assert response == "El acuario pequeño parece un rincón tranquilo de casa."
    assert len(response.split()) <= 24


def test_personality_prompt_forbids_fake_human_experiences() -> None:
    prompt = BASE_SYSTEM_PROMPT.casefold()
    assert "no finjas experiencias humanas" in prompt
    assert "a mí también me pasa" in prompt


def test_regression_sequence_keeps_operational_commands_explicit() -> None:
    sequence = (
        "reinicia telegram",
        "confirmo reiniciar telegram",
        "ayuda ia",
        "estado ia",
        "modelo ia fast",
        "hola daxter",
        "¿qué tal?",
        "dime una frase corta sobre el acuario",
        "¿qué hora es?",
        "me gusta más el invierno que el verano",
        "cambia a modo texto",
        "responde solo en modo texto",
        "¿por qué crees que te acabo de decir eso?",
        "modelo ia auto",
        "salir",
    )
    assert len(sequence) == len(set(sequence))
    assert detect_response_mode_directive(sequence[10]) is TelegramResponseMode.TEXT_ONLY
    assert detect_response_mode_directive(sequence[11]) is TelegramResponseMode.TEXT_ONLY
