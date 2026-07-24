from automation.stage_e_runtime import build_stage_e_simulation


def test_household_and_present_guests_permissions(tmp_path):
    env = build_stage_e_simulation(
        tmp_path / "automations.json",
        household_user_ids=(
            "REDACTED_f73137d930c3",
            "maria REDACTED_1ec4ed037766",
            "REDACTED_1ec4ed037766 vicente navarro",
            "REDACTED_1552db05a755",
            "REDACTED_72534c4a93dd",
        ),
        guest_user_ids=("REDACTED_7b9528898599", "raul", "amigo"),
        present_guest_user_ids=("REDACTED_7b9528898599", "raul"),
    )

    assert not env.is_guest("REDACTED_1552db05a755")
    assert env.is_guest("REDACTED_7b9528898599")
    assert env.is_guest_present("REDACTED_7b9528898599")
    assert env.is_guest_present("raul")
    assert not env.is_guest_present("amigo")
