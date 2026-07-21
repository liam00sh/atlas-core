from datetime import datetime

from daily_life.calculator import calculate_from_text
from daily_life.lists import PersonalListService
from daily_life.reminders import PersonalReminderParser
from daily_life.storage import DailyLifeStorage
from utils.intent_normalizer import interpret_text


def test_typing_interpretation_is_conservative():
    result = interpret_text("Com quien vive Raúl y dile a Saray qe compre pam")
    assert result.interpreted.startswith("Con quien")
    assert "que compre pan" in result.interpreted
    assert "Raúl" in result.interpreted
    assert "Saray" in result.interpreted


def test_relative_reminder():
    parser = PersonalReminderParser("UTC")
    now = datetime.fromisoformat("2026-07-21T10:00:00+00:00")
    result = parser.parse("Avísame dentro de 20 minutos de que saque la comida", now=now)
    assert result is not None
    assert result.message == "saque la comida"
    assert result.due_at_utc.isoformat().startswith("2026-07-21T10:20:00")


def test_absolute_reminder():
    parser = PersonalReminderParser("UTC")
    now = datetime.fromisoformat("2026-07-21T10:00:00+00:00")
    result = parser.parse("Recuérdame mañana a las 8 que llame al médico", now=now)
    assert result is not None
    assert result.message == "llame al médico"
    assert result.due_at_utc.isoformat().startswith("2026-07-22T08:00:00")


def test_personal_lists(tmp_path):
    service = PersonalListService(DailyLifeStorage(tmp_path / "daily.json"))
    assert service.create("Liam", "farmacia")
    assert service.add("Liam", "compra", ["leche", "pan"]) == ["leche", "pan"]
    assert service.remove("Liam", "compra", "pan")
    record = service.get("Liam", "compra")
    assert [item["text"] for item in record["items"]] == ["leche"]


def test_calculations():
    assert calculate_from_text("¿Cuánto son 150 euros entre tres?") == "El resultado es 50."
    assert "31,92" in calculate_from_text("Si cuesta 39,90 y tiene un 20 % de descuento, ¿cuánto vale?")
    assert "500" in calculate_from_text("¿Cuántos mililitros son 2 vasos?")
