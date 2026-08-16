from tools.analyze_home_assistant_diagnostic import analyze


def _run(initial, expected):
    return {
        "service_response": {"state": initial},
        "api_samples": [
            {"delay_seconds": 0.0, "state": initial},
            {"delay_seconds": 0.25, "state": initial},
            {"delay_seconds": 0.5, "state": expected, "last_changed": "changed", "last_updated": "updated"},
            {"delay_seconds": 1.0, "state": expected},
        ],
        "physical_observation": expected,
        "home_assistant_ui_observation": expected,
    }


def test_completed_physical_test_is_not_reproduced_but_records_stale_window():
    result = analyze({
        "actions_executed": True,
        "alias_resolution": {"entity_id": "switch.test"},
        "configured_constant_matches": True,
        "turn_on": _run("off", "on"),
        "turn_off": _run("on", "off"),
    })
    assert result["status"] == "NOT_REPRODUCED"
    assert [item["first_confirmed_api_seconds"] for item in result["actions"]] == [0.5, 0.5]
    assert all(item["service_response_was_stale"] for item in result["actions"])
    assert result["historical_bug_erased"] is False


def test_inconsistent_physical_state_keeps_bug_open():
    turn_on = _run("off", "on")
    turn_on["physical_observation"] = "off"
    result = analyze({"actions_executed": True, "turn_on": turn_on, "turn_off": _run("on", "off")})
    assert result["status"] == "STILL_OPEN"
