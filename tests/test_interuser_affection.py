from telegram_interface.interuser_delivery import InteruserMessageFormatter


def test_affection_pronouns_and_sender_capitalization():
    result = InteruserMessageFormatter.format(
        sender="REDACTED_7b9528898599",
        body="le quiero y le echo de menos",
        scheduled=False,
    )
    assert result == "REDACTED_bc04a68d9192 quiere decirte que te quiere y te echa de menos."
