from datetime import datetime

from daily_life.calculator import calculate_from_text
from daily_life.lists import PersonalListService
from daily_life.reminders import PersonalReminderParser
from daily_life.storage import DailyLifeStorage
from utils.intent_normalizer import interpret_text
from core.atlas_daily import PersonalReminderParser as CorePersonalReminderParser


def test_typing_interpretation_is_conservative():
    result = interpret_text("Com quien vive REDACTED_de9c80449aae y dile a REDACTED_bc04a68d9192 qe compre pam")
    assert result.interpreted.startswith("Con quien")
    assert "que compre pan" in result.interpreted
    assert "REDACTED_de9c80449aae" in result.interpreted
    assert "REDACTED_bc04a68d9192" in result.interpreted


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


def test_core_reminder_parser_accepts_voice_vocative_and_dotted_time():
    parser = CorePersonalReminderParser("UTC")
    now = datetime.fromisoformat("2026-08-11T05:00:00+00:00")
    result = parser.parse("Daxter, recuerdame a las 6.30 revisar el acuario", now=now)
    assert result is not None
    assert result.message == "revisar el acuario"
    assert result.due_at_utc.isoformat().startswith("2026-08-11T06:30:00")


def test_core_reminder_parser_accepts_acuerdame():
    parser = CorePersonalReminderParser("UTC")
    now = datetime.fromisoformat("2026-08-11T05:00:00+00:00")
    result = parser.parse("Acuérdame mañana a las 18:30 revisar Atlas", now=now)
    assert result is not None
    assert result.message == "revisar Atlas"


def test_core_reminder_parser_accepts_human_e2e_word_order():
    parser = CorePersonalReminderParser("UTC")
    now = datetime.fromisoformat("2026-08-21T05:00:00+00:00")
    result = parser.parse(
        "Recuérdame mañana que a las 18.30 revise Atlas", now=now
    )
    assert result is not None
    assert result.message == "revise Atlas"
    assert result.due_at_utc.isoformat().startswith("2026-08-22T18:30:00")


def test_personal_lists(tmp_path):
    service = PersonalListService(DailyLifeStorage(tmp_path / "daily.json"))
    assert service.create("REDACTED_2c7b6821719d", "farmacia")
    assert service.add("REDACTED_2c7b6821719d", "compra", ["leche", "pan"]) == ["leche", "pan"]
    assert service.remove("REDACTED_2c7b6821719d", "compra", "pan")
    record = service.get("REDACTED_2c7b6821719d", "compra")
    assert [item["text"] for item in record["items"]] == ["leche"]


def test_calculations():
    assert calculate_from_text("¿Cuánto son 150 euros entre tres?") == "El resultado es 50."
    assert "31,92" in calculate_from_text("Si cuesta 39,90 y tiene un 20 % de descuento, ¿cuánto vale?")
    assert "500" in calculate_from_text("¿Cuántos mililitros son 2 vasos?")
