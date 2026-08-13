import csv

from tools.process_final_polish_review import _group, summarize


def test_final_polish_groups_are_explicit():
    assert _group("pronunciation_es/01.wav") == "pronunciation_es"
    assert _group("english_terms/02.wav") == "english_terms"
    assert _group("names/03.wav") == "names"
    assert _group("long_sentences/04.wav") == "long_sentences"
    assert _group("trim_fade/05.wav") == "trim_fade"


def test_summary_preserves_source(tmp_path):
    source = tmp_path / "human_review.csv"
    fields = (
        "sample", "variante", "español_correcto_1_5", "pronunciacion_1_5",
        "sin_cortes_1_5", "naturalidad_1_5", "parecido_daxter_1_5",
        "preferencia", "notas",
    )
    groups = ("pronunciation_es", "english_terms", "names", "long_sentences", "trim_fade")
    with source.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(40):
            writer.writerow({
                "sample": f"{groups[index % len(groups)]}/{index:02d}.wav",
                "variante": "v1",
                "español_correcto_1_5": 4,
                "pronunciacion_1_5": 4,
                "sin_cortes_1_5": 5,
                "naturalidad_1_5": 4,
                "parecido_daxter_1_5": 4,
                "preferencia": "Mejorable",
                "notas": "Revisión sintética.",
            })
    before = source.read_bytes()
    result = summarize(source)
    assert result["source"]["rows"] == 40
    assert result["preferences"] == {"Mejorable": 40}
    assert source.read_bytes() == before
