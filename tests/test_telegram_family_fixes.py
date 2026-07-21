from telegram_interface.interuser_delivery import NaturalInteruserMessageFormatter
from telegram_interface.progress import progress_delay_for


def test_affection_message_is_natural_and_sender_capitalized():
    result = NaturalInteruserMessageFormatter.format(
        sender="saray", body="le quiero y le echo de menos", scheduled=False
    )
    assert result == "Saray quiere decirte que te quiere y te echa de menos."


def test_social_message_has_no_progress():
    assert progress_delay_for("¿Cómo estás?") < 0
