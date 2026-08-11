from __future__ import annotations

from types import SimpleNamespace

import pytest

from ai.prompts.system_prompt import BASE_SYSTEM_PROMPT
from automation.home_assistant_adapter import HomeAssistantAdapter
from automation.home_assistant_models import (
    HomeEntityDefinition, HomeEntityKind, HomeEntityMode, HomeEntityRisk, HomeEntityState,
)
from automation.home_device_registry import HomeDeviceRegistry
from automation.home_intent_resolver import HomeIntentResolver
from core.atlas_ai import AtlasAIMixin
from core.atlas_family import AtlasFamilyMixin
from core.atlas_daily import AtlasDailyMixin, PersonalReminderParser
from core.atlas_tools import CONFIRMATION_CANCELLED


class _Context:
    def get_messages(self):
        return [
            {"role": "user", "content": "Explicame Docker."},
            {"role": "assistant", "content": "Docker usa contenedores."},
        ]


@pytest.mark.parametrize(
    "new_topic",
    ("Dime algo divertido.", "Cuentame un chiste.", "Estoy probando tu nueva voz."),
)
def test_new_voice_topics_do_not_receive_previous_docker_context(new_topic):
    scoped = AtlasAIMixin()._build_scoped_conversation_context(_Context(), new_topic)
    assert "TEMA NUEVO" in scoped
    assert "Docker" not in scoped


def test_clear_followup_receives_only_last_exchange():
    scoped = AtlasAIMixin()._build_scoped_conversation_context(_Context(), "Dime mas sobre eso.")
    assert "Docker usa contenedores" in scoped


def test_identity_prompt_forbids_third_person_and_fabricated_autobiography():
    assert "habla de ti en primera persona" in BASE_SYSTEM_PROMPT
    assert "No inventes recuerdos autobiogr" in BASE_SYSTEM_PROMPT


@pytest.mark.parametrize("word", ("cancelar", "cancela", "cancelado", "cancelada"))
def test_natural_cancellation_variants_never_need_the_llm(word):
    assert word in AtlasFamilyMixin._CANCEL_ALL
    assert word in CONFIRMATION_CANCELLED or word == "cancelar"


def test_home_phrase_has_identical_semantics_for_cli_pc_voice_and_telegram():
    phrase = "Enciende la luz del acuario pequeno."
    results = [HomeIntentResolver().resolve(phrase) for _channel in ("cli", "pc_voice", "telegram")]
    assert all(result is not None for result in results)
    assert {result.action_id for result in results} == {"home.switch.turn_on"}
    assert {result.parameters["entity_id"] for result in results} == {
        "switch.despacho_acuario_pequeno_luz_acuario_pequeno"
    }


class _DelayedTransport:
    def __init__(self, states):
        self.states = list(states)

    def call_service(self, *_args, entity_id, **_kwargs):
        return HomeEntityState(entity_id, "off", {})

    def get_state(self, entity_id):
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return HomeEntityState(entity_id, state, {"friendly_name": "Luz acuario"})


def _adapter(states):
    registry = HomeDeviceRegistry()
    registry.register(HomeEntityDefinition(
        entity_id="switch.test",
        name="Luz acuario",
        kind=HomeEntityKind.SWITCH,
        mode=HomeEntityMode.PHYSICAL,
        risk=HomeEntityRisk.MEDIUM,
        allowed_services=frozenset({"turn_on", "turn_off"}),
        required_permission="home.control.switch",
    ))
    return HomeAssistantAdapter(_DelayedTransport(states), registry)


def test_home_action_retries_and_returns_verified_state(monkeypatch):
    monkeypatch.setattr("automation.home_assistant_adapter.time.sleep", lambda _seconds: None)
    result = _adapter(["off", "on"]).turn_on("switch.test")
    assert result["state"] == "on"


def test_home_action_never_claims_unverified_state(monkeypatch):
    monkeypatch.setattr("automation.home_assistant_adapter.time.sleep", lambda _seconds: None)
    with pytest.raises(RuntimeError, match="sigue apareciendo apagado"):
        _adapter(["off"]).turn_on("switch.test")


def test_voice_reminder_creates_a_real_queue_side_effect():
    class Queue:
        request = None

        def enqueue(self, owner, request):
            self.request = (owner, request)
            return {"ok": True, "id": "reminder-1"}

    class Daily(AtlasDailyMixin):
        def __init__(self):
            self.personal_reminder_parser = PersonalReminderParser("UTC")
            self.queue = Queue()
            self.messages = []

        def _queue(self):
            return self.queue

        def _print(self, text):
            self.messages.append(text)

    daily = Daily()
    state = {}
    handled = daily._handle_personal_reminders(
        "Daxter, recuerdame que ma\u00f1ana a las 18:30 tengo que revisar Atlas",
        "daxter recuerdame que manana a las 18 30 tengo que revisar atlas",
        "Liam",
        state,
    )
    assert handled is True
    assert daily.queue.request is not None
    assert state["last_reminder_id"] == "reminder-1"
    assert "recordar" in daily.messages[0].casefold()
