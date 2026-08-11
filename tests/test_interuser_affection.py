from telegram_interface.interuser_delivery import InteruserMessageFormatter


def test_affection_pronouns_and_sender_capitalization():
    result = InteruserMessageFormatter.format(
        sender="Vega",
        body="le quiero y le echo de menos",
        scheduled=False,
    )
    assert result == "Vega quiere decirte que te quiere y te echa de menos."
