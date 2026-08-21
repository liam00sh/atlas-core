from tools.analyze_tts_boundary_human_review import aggregate, classify, normalized_evaluation, validate


HEADERS = [
    "blind_id", "case", "complete_start_1_5", "complete_end_1_5",
    "naturalness_1_5", "artifacts_1_5", "accept", "notes",
]


def test_human_review_normalization_preserves_notes_and_validates_ranges():
    rows = normalized_evaluation(HEADERS, [{
        "blind_id": "M001", "case": "12", "complete_start_1_5": "5",
        "complete_end_1_5": "5", "naturalness_1_5": "3",
        "artifacts_1_5": "5", "accept": "si",
        "notes": '"Home" mal pronunciado',
    }])
    assert rows[0]["case"] == 12
    assert rows[0]["accept"] == "SI"
    assert rows[0]["notes"] == '"Home" mal pronunciado'
    result = validate(rows)
    assert result["errors"] == ["Se esperaban 70 filas y hay 1"]


def test_boundary_flags_do_not_mix_pronunciation_with_cuts_or_artifacts():
    row = {
        "complete_start_1_5": 5, "complete_end_1_5": 5,
        "naturalness_1_5": 3, "artifacts_1_5": 5,
        "notes": '"Home" mal pronunciado',
    }
    flags = classify(row)
    assert flags["pronunciation_issue"] is True
    assert flags["initial_cut"] is flags["final_cut"] is False
    assert flags["confirmed_artifact"] is False


def test_boundary_ranking_inputs_expose_hard_cut_and_limit_counts():
    complete = [{
        "complete_start_1_5": 5, "complete_end_1_5": 5,
        "naturalness_1_5": 4, "artifacts_1_5": 5,
        "accept": "SI", "notes": "", "reached_generation_limit": False,
    } for _ in range(7)]
    result = aggregate(complete, "E_candidate")
    assert result["initial_cuts"] == result["final_cuts"] == 0
    assert result["reached_generation_limit"] == 0
    assert result["accept_si_pct"] == 100.0
