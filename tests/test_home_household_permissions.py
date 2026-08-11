from automation.stage_e_runtime import build_stage_e_simulation


def test_household_and_present_guests_permissions(tmp_path):
    env = build_stage_e_simulation(
        tmp_path / "automations.json",
        household_user_ids=(
            "Alex",
            "Zoe Soler",
            "Zoe Vidal",
            "Carla",
            "Diego",
        ),
        guest_user_ids=("Vega", "raul", "amigo"),
        present_guest_user_ids=("Vega", "raul"),
    )

    assert not env.is_guest("Carla")
    assert env.is_guest("Vega")
    assert env.is_guest_present("Vega")
    assert env.is_guest_present("raul")
    assert not env.is_guest_present("amigo")
