import csv
import json

import pytest

from tools.close_daxter_round_b import aggregate, load_inputs


def test_load_inputs_rejects_non_bijective_key(tmp_path):
    csv_path = tmp_path / "human.csv"
    key_path = tmp_path / "key.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["blind_code"])
        writer.writeheader()
        writer.writerow({"blind_code": "RB0001"})
    key_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="136"):
        load_inputs(csv_path, key_path)


def test_aggregate_keeps_batteries_separate():
    rows = []
    for candidate in ("B0", "B1", "B2", "B3"):
        for battery, count in (("corrected", 21), ("original", 13)):
            for _ in range(count):
                row = {"candidate": candidate, "battery": battery, "preferencia": "SI"}
                row.update({field: 5.0 for field in (
                    "naturalidad_1_5", "inteligibilidad_1_5", "similitud_daxter_1_5", "emocion_1_5",
                    "pronunciacion_1_5", "espanol_espana_1_5", "inicio_sin_cortes_1_5",
                    "estabilidad_1_5", "artefactos_1_5",
                )})
                rows.append(row)
    result = aggregate(rows)
    assert result["B0"]["corrected"]["samples"] == 21
    assert result["B0"]["original"]["samples"] == 13
    assert result["B0"]["global"]["samples"] == 34
