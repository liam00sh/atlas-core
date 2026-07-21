from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from telegram_interface.interuser_delivery import (
    InteruserRequestParser,
    NaturalInteruserMessageFormatter,
    TelegramDeliveryDispatcher,
    TelegramDeliveryQueue,
)
from telegram_interface.storage import TelegramStorage


class FakeClient:
    def __init__(self):
        self.sent = []

    def send_message(self, *, chat_id, text, parse_mode=None):
        self.sent.append((str(chat_id), text, parse_mode))
        return {"message_id": 1}


def linked_storage(tmp_path):
    storage = TelegramStorage(tmp_path / "state.json")

    def mutate(data):
        data["accounts"] = {
            "100": {"state": "linked", "atlas_user_id": "REDACTED_2c7b6821719d", "chat_id": "500"},
            "200": {"state": "linked", "atlas_user_id": "REDACTED_bc04a68d9192", "chat_id": "600"},
        }

    storage.update(mutate)
    return storage


def test_immediate_message_is_generic_and_delivered(tmp_path):
    storage = linked_storage(tmp_path)
    queue = TelegramDeliveryQueue(storage)
    parser = InteruserRequestParser("Europe/Madrid")
    request = parser.parse("recuérdale a REDACTED_bc04a68d9192 que compre pan", linked_user_ids=queue.linked_users())
    assert request is not None and request.scheduled is False
    created = queue.enqueue("REDACTED_2c7b6821719d", request)
    assert created["ok"] is True

    client = FakeClient()
    assert TelegramDeliveryDispatcher(queue, client).deliver_due() == 1
    assert client.sent == [("600", "REDACTED_2c7b6821719d te recuerda que compres pan.", None)]


def test_scheduled_message_accepts_spanish_time(tmp_path):
    storage = linked_storage(tmp_path)
    queue = TelegramDeliveryQueue(storage)
    parser = InteruserRequestParser("Europe/Madrid")
    request = parser.parse(
        "recuerda a REDACTED_bc04a68d9192 a las 17 que vaya al mercado",
        linked_user_ids=queue.linked_users(),
        now=datetime(2026, 7, 20, 16, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )
    assert request is not None and request.scheduled is True
    assert request.message == "vaya al mercado"
    assert request.due_at_utc == datetime(2026, 7, 20, 15, 0, tzinfo=UTC)


def test_target_must_be_linked(tmp_path):
    storage = linked_storage(tmp_path)
    queue = TelegramDeliveryQueue(storage)
    parser = InteruserRequestParser()
    assert parser.parse("dile a REDACTED_0392c3d1b4d3 que llame", linked_user_ids=queue.linked_users()) is None


def test_affection_message_is_natural():
    assert NaturalInteruserMessageFormatter.format(
        sender="REDACTED_2c7b6821719d",
        body="la quiero mucho",
        scheduled=False,
    ) == "REDACTED_2c7b6821719d quiere que sepas que te quiere mucho."


def test_household_task_is_rewritten_for_recipient():
    assert NaturalInteruserMessageFormatter.format(
        sender="REDACTED_2c7b6821719d",
        body="ponga la lavadora",
        scheduled=False,
    ) == "REDACTED_2c7b6821719d te recuerda que pongas la lavadora."


def test_personal_obligation_changes_to_second_person():
    assert NaturalInteruserMessageFormatter.format(
        sender="REDACTED_2c7b6821719d",
        body="se tiene que ir a cortar el pelo",
        scheduled=False,
    ) == "REDACTED_2c7b6821719d te recuerda que te tienes que ir a cortar el pelo."
