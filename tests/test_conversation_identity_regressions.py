"""Regresiones de identidad sobre personas completamente ficticias."""

from types import SimpleNamespace

from ai.providers.ollama_provider import OllamaProvider
from conversation import personality
from core.atlas_ai import AtlasAIMixin


class _IdentityManager:
    def __init__(self, identity="Daxter", mode="classic"):
        self.identity = identity
        self.mode = mode

    def get_active_display_name(self):
        return self.identity

    def get_active_mode_name(self):
        return self.mode


def test_identity_answer_is_not_repeated_consecutively():
    first = personality.identity("Coco", "Proyecto Atlas")
    second = personality.identity("Coco", "Proyecto Atlas")
    assert first != second


def test_ordinal_variants_are_accepted():
    variants = {"1": 0, "primera": 0, "la segunda": 1, "segundo": 1}
    for text, expected in variants.items():
        assert AtlasAIMixin._parse_ordinal_selection(text) == expected


def test_identity_and_current_user_use_different_topic_keys():
    assistant = AtlasAIMixin._response_topic_key("quien eres", "Alex")
    user = AtlasAIMixin._response_topic_key("quien soy", "Alex")
    assert assistant != user
    assert assistant.endswith("identidad_asistente")
    assert user.endswith("identidad_interlocutor")


def test_verified_response_style_depends_on_identity():
    atlas = AtlasAIMixin()
    atlas.identity_manager = _IdentityManager("Daxter", "classic")
    daxter = atlas._style_verified_response(
        "Carla es familiar de Alex.", response_kind="biography"
    )
    atlas.identity_manager = _IdentityManager("Coco", "classic")
    coco = atlas._style_verified_response(
        "Carla es familiar de Alex.", response_kind="biography"
    )
    assert daxter.startswith("Vale, te pongo en situación:")
    assert coco.startswith("Claro, te cuento:")


def test_cleanup_preserves_valid_unpunctuated_greeting():
    cleaned = OllamaProvider._clean_generated_text(
        "Hola Alex es el usuario principal de Atlas.",
        "MENSAJE DEL USUARIO:\nquien es Alex\n\n",
    )
    assert cleaned == "Hola Alex es el usuario principal de Atlas."


def test_cleanup_removes_model_prefix_and_english_filler():
    prompt = (
        "Animal mencionado: Nube.\n"
        "Nombre habitual preferido: Nube.\n"
        "Responde ahora como Coco."
    )
    dirty = "Daxter: Perhaps te refieres a Nube."
    cleaned = OllamaProvider._clean_generated_text(dirty, prompt)
    assert "Daxter:" not in cleaned
    assert "Perhaps" not in cleaned


def test_relationship_context_uses_speaker_perspective():
    atlas = AtlasAIMixin()
    speaker = SimpleNamespace(
        id="alex", name="Alex", aliases=[], summary="Ficticio.", user_profile="Alex"
    )
    person = SimpleNamespace(
        id="vega",
        name="Vega Ferrer",
        aliases=["Vega"],
        summary="Ficticia.",
        user_profile="Vega",
    )
    atlas.people_manager = SimpleNamespace(
        get_people=lambda: [speaker, person],
        get_animals=lambda: [],
        find_person_by_name=lambda name: speaker if name.casefold() == "alex" else None,
    )
    atlas.relationship_engine = SimpleNamespace(
        describe_relationships_for_entity=lambda **_kwargs: [
            "Vega Ferrer es pareja de Alex."
        ],
        describe_relationship_between_entities=lambda **_kwargs: (
            "Vega Ferrer es pareja de Alex."
        ),
    )
    atlas.identity_manager = _IdentityManager()
    atlas._get_current_conversation_user = lambda: "Alex"
    context = atlas._build_referenced_entities_context("quien es Vega")
    assert "Interlocutor actual: Alex" in context


def test_similarity_detection_rejects_repeated_answers():
    assert AtlasAIMixin._responses_are_too_similar(
        "Vega es pareja de Alex.", "Vega es pareja de Alex."
    )
    assert not AtlasAIMixin._responses_are_too_similar(
        "Vega es pareja de Alex.", "Carla cuida de Brisa."
    )
