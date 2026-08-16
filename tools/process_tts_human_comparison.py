"""Procesa una comparación TTS ciega sin modificar la evaluación humana."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import tempfile


DIMENSIONS = (
    "parecido_daxter_1_5",
    "espanol_espana_1_5",
    "naturalidad_1_5",
    "pronunciacion_1_5",
    "ritmo_entonacion_1_5",
    "artefactos_cortes_1_5",
)
PRIORITY_WEIGHTS = dict(zip(DIMENSIONS, (6, 5, 4, 3, 2, 1), strict=True))
CATEGORY_RANGES = (
    (range(1, 11), "tildes_espanol"),
    (range(11, 15), "nombres"),
    (range(15, 21), "terminos_ingleses"),
    (range(21, 24), "numeros_fechas"),
    (range(24, 27), "frases_largas"),
    (range(27, 29), "interrogaciones_exclamaciones"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phrase_category(blind_id: str) -> str:
    match = re.fullmatch(r"TTS(\d{3})_[ABC]", blind_id)
    if match is None:
        raise ValueError(f"Identificador ciego inválido: {blind_id}")
    number = int(match.group(1))
    for numbers, category in CATEGORY_RANGES:
        if number in numbers:
            return category
    raise ValueError(f"Caso fuera de las 28 frases: {blind_id}")


def classify_note(note: str) -> list[str]:
    value = note.casefold()
    labels: list[str] = []
    accent_words = (
        "acción", "función", "está", "información", "infomración", "revisión",
        "aplicación", "explicación", "precisión", "pronunciación", "emoción",
        "opción", "aquí", "mañana", "revisaré", "cómo", "comprobación",
        "avisaré", "qué", "conversación", "acento", "accento",
    )
    if any(word in value for word in accent_words):
        labels.append("acentos_tildes")
    if any(word in value for word in ("español", "castellan", "portugues", "canario")):
        labels.append("pronunciacion_castellana")
    if any(word in value for word in ("home", "github", "wi-fi", "docker", "telegram", "google drive")):
        labels.append("terminos_ingleses")
    if "princip" in value or "al inicio" in value or "se corta al inicio" in value:
        labels.append("corte_inicial")
    if "final se corta" in value or "se corta al final" in value:
        labels.append("corte_final")
    if "artefact" in value:
        labels.append("artefactos")
    if any(word in value for word in ("poco natural", "ritmo", "muy acentuado", "palabras raras")):
        labels.append("ritmo_extrano")
    return labels


def _mean(rows: list[dict], field: str) -> float:
    return round(sum(float(row[field]) for row in rows) / len(rows), 4)


def analyze_rows(rows: list[dict], mapping: dict, automatic: dict) -> dict:
    audio_rows = [row for row in rows if str(row.get("blind_id", "")).strip()]
    general_rows = [row for row in rows if not str(row.get("blind_id", "")).strip()]
    if len(audio_rows) != 84:
        raise ValueError(f"Se esperaban 84 evaluaciones de audio; hay {len(audio_rows)}.")
    if len(general_rows) != 1:
        raise ValueError("Debe existir exactamente una fila final de notas generales.")
    if set(row["blind_id"] for row in audio_rows) != set(mapping):
        raise ValueError("Los blind_id humanos no coinciden exactamente con la clave ciega.")
    grouped: dict[str, list[dict]] = defaultdict(list)
    ranks: dict[str, Counter] = defaultdict(Counter)
    category_rows: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    comment_classes: dict[str, Counter] = defaultdict(Counter)
    comments: dict[str, list[dict]] = defaultdict(list)
    group_ranks: dict[str, list[int]] = defaultdict(list)

    for row in audio_rows:
        blind_id = row["blind_id"]
        candidate = mapping[blind_id]["candidate"]
        for dimension in DIMENSIONS:
            score = float(row[dimension])
            if not 1 <= score <= 5:
                raise ValueError(f"Puntuación fuera de 1..5 en {blind_id}/{dimension}.")
        rank_match = re.match(r"\s*([123])", str(row.get("preferido_en_grupo", "")))
        if rank_match is None:
            raise ValueError(f"Preferencia inválida en {blind_id}.")
        rank = int(rank_match.group(1))
        group_ranks[blind_id[:6]].append(rank)
        ranks[candidate][rank] += 1
        grouped[candidate].append(row)
        category_rows[candidate][phrase_category(blind_id)].append(row)
        note = str(row.get("notas", "")).strip()
        labels = classify_note(note)
        if note:
            comments[candidate].append({
                "blind_id": blind_id,
                "frase": row["frase"],
                "comentario": note,
                "clasificaciones": labels,
            })
            comment_classes[candidate].update(labels)
    # A malformed human ranking is evidence, not permission to rewrite the source.
    # Keep it in the counts and surface it explicitly for the final decision.
    ranking_anomalies = [
        {"phrase_id": group, "recorded_ranks": values}
        for group, values in sorted(group_ranks.items())
        if sorted(values) != [1, 2, 3]
    ]

    by_model = {}
    for candidate, candidate_rows in grouped.items():
        means = {dimension: _mean(candidate_rows, dimension) for dimension in DIMENSIONS}
        global_mean = round(sum(means.values()) / len(DIMENSIONS), 4)
        weighted = round(
            sum(means[name] * weight for name, weight in PRIORITY_WEIGHTS.items())
            / sum(PRIORITY_WEIGHTS.values()),
            4,
        )
        by_category = {}
        for category, values in category_rows[candidate].items():
            category_means = {dimension: _mean(values, dimension) for dimension in DIMENSIONS}
            by_category[category] = {
                "samples": len(values),
                "means": category_means,
                "global_mean": round(sum(category_means.values()) / len(DIMENSIONS), 4),
            }
        metric_data = automatic.get("candidates", {}).get(candidate, {})
        metric_results = metric_data.get("results", [])
        by_model[candidate] = {
            "model": mapping[next(row["blind_id"] for row in candidate_rows)]["model"],
            "samples": len(candidate_rows),
            "means": means,
            "global_mean": global_mean,
            "priority_weighted_mean": weighted,
            "rank_counts": {"first": ranks[candidate][1], "second": ranks[candidate][2], "third": ranks[candidate][3]},
            "by_phrase_category": by_category,
            "comment_class_counts": dict(sorted(comment_classes[candidate].items())),
            "comments": comments[candidate],
            "automatic_metrics": {
                "device": metric_data.get("device"),
                "failures": sum(not bool(item.get("success")) for item in metric_results),
                "possible_truncations": sum(bool(item.get("possible_truncation")) for item in metric_results),
            },
        }

    ordered = sorted(
        by_model,
        key=lambda name: (
            by_model[name]["rank_counts"]["first"],
            by_model[name]["priority_weighted_mean"],
            by_model[name]["global_mean"],
        ),
        reverse=True,
    )
    winner, runner_up = ordered[:2]
    general_note = str(general_rows[0].get("notas", "")).strip()
    return {
        "schema_version": 1,
        "human_evaluations": len(audio_rows),
        "phrase_groups": len(group_ranks),
        "general_human_note": general_note,
        "general_note_classifications": classify_note(general_note),
        "priority_order": list(DIMENSIONS),
        "models": by_model,
        "ranking": ordered,
        "data_integrity": {
            "ranking_anomalies": ranking_anomalies,
            "human_values_modified": False,
        },
        "winner": winner,
        "runner_up": runner_up,
    }


def decision_from_results(results: dict, manifest: dict) -> dict:
    winner = results["winner"]
    runner_up = results["runner_up"]
    winner_data = results["models"][winner]
    runner_data = results["models"][runner_up]
    identity_gap = round(
        winner_data["means"]["parecido_daxter_1_5"]
        - runner_data["means"]["parecido_daxter_1_5"],
        4,
    )
    return {
        "schema_version": 1,
        "winner": winner,
        "winner_model": winner_data["model"],
        "runner_up": runner_up,
        "runner_up_model": runner_data["model"],
        "decision_kind": "human_blind_comparison",
        "candidate_configuration_frozen": True,
        "frozen_configuration": {
            "shared_controls": manifest.get("shared_controls", {}),
            "reference_file": manifest.get("reference_file"),
            "postprocess": manifest.get("postprocess"),
            "generation_safety": manifest.get("generation_safety"),
        },
        "reason": (
            "El modelo es-ES obtiene más primeros puestos, la mejor media global y el mejor español de España, "
            "sin una pérdida grande de parecido con Daxter frente a V2. La configuración queda congelada como "
            "candidata; no cierra Fase 6 ni elimina los defectos de acentos observados."
        ),
        "identity_tradeoff_vs_runner_up": identity_gap,
        "advantages": ["mejor español de España", "menos artefactos/cortes", "más primeros puestos"],
        "defects": ["acentos y palabras con tilde", "naturalidad y ritmo aún por debajo del objetivo", "cortes puntuales"],
        "problematic_words": ["acción", "función", "está", "información"],
        "additional_tests_required": ["STT humana 160/160", "prueba E2E posterior", "regresión dirigida de palabras con tilde"],
        "phase_6_closed": False,
    }


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def _markdown(results: dict, decision: dict, source_name: str) -> str:
    lines = [
        "# Resultado humano de la comparación TTS", "",
        f"Fuente humana: `{source_name}` (84 evaluaciones + una nota general).", "",
        f"Ganador humano: **{decision['winner_model']}** (`{decision['winner']}`).", "",
        f"Segundo: **{decision['runner_up_model']}** (`{decision['runner_up']}`).", "",
        "La configuración se congela como candidata, no como cierre de Fase 6.", "",
        "## Medias y preferencias", "",
        "| Modelo | Daxter | España | Naturalidad | Pronunciación | Ritmo | Sin artefactos | Global | 1º/2º/3º |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in results["ranking"]:
        item = results["models"][name]
        m, r = item["means"], item["rank_counts"]
        lines.append(
            f"| {item['model']} | {m['parecido_daxter_1_5']:.3f} | {m['espanol_espana_1_5']:.3f} | "
            f"{m['naturalidad_1_5']:.3f} | {m['pronunciacion_1_5']:.3f} | {m['ritmo_entonacion_1_5']:.3f} | "
            f"{m['artefactos_cortes_1_5']:.3f} | {item['global_mean']:.3f} | {r['first']}/{r['second']}/{r['third']} |"
        )
    lines += [
        "", "## Conclusión", "", decision["reason"], "",
        "## Nota humana general", "", results["general_human_note"], "",
        "## Defectos que permanecen", "",
        "- Acentos y palabras con tilde: acción, función, está e información.",
        "- El es-ES conserva ligeramente menos identidad que V2, aunque la diferencia es pequeña.",
        "- Deben revisarse los cortes puntuales y la naturalidad/entonación antes del cierre.",
        "", "Las métricas automáticas se conservan como diagnóstico y no decidieron el ganador.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-csv", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--automatic-metrics", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source_hash = _sha256(args.human_csv)
    with args.human_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    key = json.loads(args.blind_key.read_text(encoding="utf-8"))
    automatic = json.loads(args.automatic_metrics.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    results = analyze_rows(rows, key["mapping"], automatic)
    results["source"] = {"file": args.human_csv.name, "sha256": source_hash, "modified": False}
    decision = decision_from_results(results, manifest)
    _atomic_text(args.output_dir / "TTS_MODEL_COMPARISON_HUMAN_RESULTS.json", json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    _atomic_text(args.output_dir / "TTS_MODEL_COMPARISON_HUMAN_RESULTS.md", _markdown(results, decision, args.human_csv.name))
    _atomic_text(args.output_dir / "TTS_MODEL_FINAL_DECISION.json", json.dumps(decision, ensure_ascii=False, indent=2) + "\n")
    if _sha256(args.human_csv) != source_hash:
        raise RuntimeError("La fuente humana cambió durante el procesamiento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
