from dataclasses import dataclass

import pytest

from conversation.continuity_store import ConversationContinuityStore
from core.atlas import Atlas
from core.atlas_daily import DailyLifeStorage, PersonalListService
from core import context


@dataclass
class FakeProvider:
    model: str
    answers: list[object]

    def is_available(self):
        return True

    def is_model_installed(self):
        return True

    def generate(self, _prompt):
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return str(answer)

    def get_provider_name(self):
        return "fake-local"

    def get_model_name(self):
        return self.model


@pytest.fixture
def atlas_core(tmp_path):
    atlas = Atlas(ai_provider=None)
    context.atlas = atlas
    atlas.conversation_continuity = ConversationContinuityStore(
        tmp_path / "continuity.json"
    )
    atlas._daily_bootstrap()
    atlas.daily_storage = DailyLifeStorage(tmp_path / "daily_state.json")
    atlas.personal_lists = PersonalListService(atlas.daily_storage)
    atlas._daily_session_state = {}
    return atlas
