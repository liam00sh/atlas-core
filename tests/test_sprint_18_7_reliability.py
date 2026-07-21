from contextlib import redirect_stdout
from io import StringIO

from core.atlas_ai import AtlasAIMixin
from core.atlas_social import AtlasSocialMixin


class _Identity:
    def get_active_display_name(self):
        return "Daxter"


class _SocialAtlas(AtlasSocialMixin):
    identity_manager = _Identity()

    def _get_current_conversation_user(self):
        return "Liam"

    def get_user(self):
        return "Liam"



def test_common_greetings_are_deterministic():
    atlas = _SocialAtlas()
    for greeting in ("Buenas tardes", "Buenas noches", "Buenos días", "Hola qué tal", "Hey", "Hi"):
        output = StringIO()
        with redirect_stdout(output):
            assert atlas._handle_social_conversation(greeting) is True
        assert output.getvalue().strip()


def test_explicit_internet_query_is_extracted_without_reasking_permission():
    assert AtlasAIMixin._extract_explicit_internet_query(
        "Busca en Internet cuántos habitantes tiene Beneixama"
    ) == "cuantos habitantes tiene beneixama"


def test_translation_languages_include_requested_common_languages():
    languages = AtlasAIMixin._supported_translation_languages()
    for language in ("ingles", "valenciano", "catalan", "frances", "portugues", "italiano", "aleman"):
        assert language in languages
