from tools.build_stt_conversation_battery import rows
from tools.evaluate_stt_conversation_battery import evaluate


def test_battery_has_160_balanced_cases_without_private_names():
    battery = rows()
    assert len(battery) == 160
    assert {row["category"] for row in battery} == {
        "conversation", "commands", "home_assistant", "reminders",
        "people", "tools", "confirmation", "continuity",
    }
    assert all("persona conocida" in row["expected_text"].casefold() for row in battery if row["category"] == "people")


def test_unmeasured_rows_cannot_be_reported_as_accuracy():
    report = evaluate(rows())
    assert report["measured_cases"] == 0
    assert report["wer"] is None
    assert report["valid_for_release_claim"] is False
