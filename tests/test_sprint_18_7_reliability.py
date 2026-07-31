from contextlib import redirect_stdout
from io import StringIO

import core.atlas_daily_brief as daily_brief
from core.atlas_ai import AtlasAIMixin
from core.atlas_daily_brief import AtlasDailyBriefMixin
from core.atlas_social import AtlasSocialMixin
from core.guest_session import GuestSessionManager


class _Identity:
    def get_active_display_name(self):
        return "Daxter"


class _SocialAtlas(AtlasSocialMixin):
    identity_manager = _Identity()

    def __init__(self, *, guest_name=None, pending_guest=None):
        self.guest_sessions = GuestSessionManager()
        if guest_name:
            self.guest_sessions.start(
                host_user="REDACTED_2c7b6821719d",
                guest_name=guest_name,
                assistant_name="Daxter",
            )
        if pending_guest:
            self.guest_sessions.set_pending_guest(pending_guest)
        self.social_reply_choice = lambda replies: replies[0]

    def _get_current_conversation_user(self):
        guest = self.guest_sessions.get()
        if guest is not None:
            return guest.guest_name
        return "REDACTED_2c7b6821719d"

    def get_user(self):
        return "REDACTED_2c7b6821719d"


class _DailyGreetingAtlas(AtlasDailyBriefMixin):
    def get_user(self):
        return "REDACTED_2c7b6821719d"

    def _brief_reminders(self, owner, *, tomorrow=False):
        return []

    def _optional_brief_items(self, hook_name, owner, target_date):
        return []


def _greeting_output(text, *, social=None, daily=None):
    social = social or _SocialAtlas()
    daily = daily or _DailyGreetingAtlas()
    output = StringIO()
    with redirect_stdout(output):
        handled = daily._handle_daily_brief(text)
        if not handled:
            handled = social._handle_social_conversation(text)
    return handled, output.getvalue().strip()



def test_common_greetings_are_deterministic(monkeypatch):
    monkeypatch.setattr(
        daily_brief,
        "_weather_answer",
        lambda text, location: "Tiempo simulado sin red.",
    )
    for greeting in (
        "Buenos días", "Buenas tardes", "Buenas noches", "Hola", "Hola qué tal",
    ):
        first = _greeting_output(greeting)
        second = _greeting_output(greeting)
        assert first == second
        assert first[0] is True
        assert first[1]


def test_identified_and_guest_greetings_use_the_injected_session_state():
    identified = _SocialAtlas()
    guest = _SocialAtlas(guest_name="José")

    assert "REDACTED_2c7b6821719d" in _greeting_output("Hola", social=identified)[1]
    assert "José" in _greeting_output("Hola", social=guest)[1]


def test_new_existing_and_pending_guest_sessions_do_not_leak_state():
    new_session = _SocialAtlas()
    pending_session = _SocialAtlas(pending_guest="REDACTED_aebac53c46bb")
    existing_session = _SocialAtlas(guest_name="REDACTED_bc04a68d9192")

    assert new_session.guest_sessions.get() is None
    assert pending_session.guest_sessions.get_pending_guest() == "REDACTED_aebac53c46bb"
    assert existing_session.guest_sessions.get().guest_name == "REDACTED_bc04a68d9192"
    assert "REDACTED_2c7b6821719d" in _greeting_output("Buenas tardes", social=pending_session)[1]
    assert "REDACTED_bc04a68d9192" in _greeting_output("Buenas tardes", social=existing_session)[1]


def test_explicit_internet_query_is_extracted_without_reasking_permission():
    assert AtlasAIMixin._extract_explicit_internet_query(
        "Busca en Internet cuántos habitantes tiene REDACTED_a77d7bb7adbf"
    ) == "cuantos habitantes tiene REDACTED_fddd19092a14"


def test_translation_languages_include_requested_common_languages():
    languages = AtlasAIMixin._supported_translation_languages()
    for language in ("ingles", "valenciano", "catalan", "frances", "portugues", "italiano", "aleman"):
        assert language in languages
