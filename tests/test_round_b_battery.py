from tools.round_b_battery import CANDIDATES, battery, normalize_for_inference


def test_round_b_has_four_candidates_and_both_batteries():
    assert tuple(CANDIDATES) == ("B0", "B1", "B2", "B3")
    assert len(battery("original")) == 13
    assert len(battery("corrected")) == 21
    assert any(case_id == "16_jak_espera" for case_id, _, _ in battery("corrected"))


def test_inference_normalization_is_explicit_and_non_destructive():
    source = "Jak y Daxter probarán Atlas con Home Assistant y Telegram."
    result = normalize_for_inference(source)
    assert source == "Jak y Daxter probarán Atlas con Home Assistant y Telegram."
    assert result == "Yak y Dákster probarán Átlas con Joum Asístent y Télegram."
