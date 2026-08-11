from tools.build_daxter_personality_lab import build_cases, player_html


def test_personality_lab_has_forty_cases_and_required_contexts():
    cases = build_cases()
    assert len(cases) == 40
    request_types = {case["request_type"] for case in cases}
    assert {"greeting", "error", "success", "technical", "privacy", "security", "driving", "emergency"} <= request_types


def test_every_personality_case_preserves_base_content():
    for case in build_cases():
        assert case["respuesta_base"] in case["respuesta_daxter"]


def test_emergency_and_driving_force_low_strength():
    cases = build_cases()
    serious = [case for case in cases if case["request_type"] in {"emergency", "driving"}]
    assert serious
    assert all(case["personality_strength"] == "low" for case in serious)


def test_personality_html_renders_all_cases():
    rendered = player_html(build_cases())
    assert rendered.count("<article") == 40
    assert "P040" in rendered
