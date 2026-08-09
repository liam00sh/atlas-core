from tools.voice_lab_battery import BATTERY


def test_battery_has_required_cases_and_unique_ids():
    ids = [case_id for case_id, _ in BATTERY]
    assert len(BATTERY) >= 13
    assert len(ids) == len(set(ids))
    for required in ("neutral", "sonriente", "travieso", "sorprendido", "emocionado", "asustado", "enfadado", "curioso", "confiado", "determinado", "jugueton", "numeros_nombres", "larga"):
        assert any(required in case_id for case_id in ids)
