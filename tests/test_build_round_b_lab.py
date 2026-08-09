from tools.build_round_b_lab import round_a_summary


def test_round_a_summary_preserves_human_decision(tmp_path):
    path = tmp_path / "human.csv"
    path.write_text(
        "audio_file,naturalidad_1_5,inteligibilidad_1_5,similitud_daxter_1_5,emocion_1_5,pronunciacion_1_5,estabilidad_1_5,artefactos_1_5,preferencia\n"
        "engine_chatterbox_multilingual/a.wav,5,5,5,4,3,5,5,SI\n"
        "engine_openvoice_v2/a.wav,4,5,2,4,3,5,4,NO\n",
        encoding="utf-8",
    )
    result = round_a_summary(path)
    assert result["engines"]["chatterbox"]["metrics"]["similitud_daxter_1_5"] == 5.0
    assert result["engines"]["openvoice"]["preferences"] == {"no": 1}
