"""Resume la revisión humana final sin modificar el CSV de origen."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


GROUPS = (
    "pronunciation_es",
    "english_terms",
    "names",
    "long_sentences",
    "trim_fade",
)
SCORE_FIELDS = (
    "español_correcto_1_5",
    "pronunciacion_1_5",
    "sin_cortes_1_5",
    "naturalidad_1_5",
    "parecido_daxter_1_5",
)


def _group(sample: str) -> str:
    value = sample.casefold().replace("\\", "/")
    aliases = {
        "pronunciation_es": ("pronunciation", "pronunciacion"),
        "english_terms": ("english", "ingles"),
        "long_sentences": ("long", "larga"),
        "trim_fade": ("trim", "fade"),
        "names": ("name", "nombre"),
    }
    for group, needles in aliases.items():
        if any(needle in value for needle in needles):
            return group
    raise ValueError(f"No se puede clasificar la muestra: {sample}")


def summarize(csv_path: Path) -> dict:
    original_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 40:
        raise ValueError(f"Se esperaban 40 filas y se encontraron {len(rows)}")

    grouped: dict[str, list[dict]] = defaultdict(list)
    preferences = Counter()
    for row in rows:
        group = _group(row["sample"])
        preferences[row["preferencia"].strip()] += 1
        grouped[group].append(row)

    groups = {}
    for group in GROUPS:
        entries = grouped[group]
        scores = {
            field: round(sum(float(row[field]) for row in entries) / len(entries), 3)
            for field in SCORE_FIELDS
        }
        notes = [row["notas"].strip() for row in entries if row["notas"].strip()]
        groups[group] = {
            "samples": len(entries),
            "preferences": dict(Counter(row["preferencia"].strip() for row in entries)),
            "average_scores": scores,
            "human_notes": notes,
        }

    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "filename": csv_path.name,
            "sha256": original_hash,
            "rows": len(rows),
            "modified": False,
        },
        "preferences": dict(preferences),
        "groups": groups,
        "decision": {
            "winner": None,
            "phase_6_closed": False,
            "reason": "La revisión humana no acredita un ganador global ni el objetivo de español de España.",
        },
    }
    if hashlib.sha256(csv_path.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("El CSV cambió durante el procesamiento")
    return result


def render_markdown(result: dict) -> str:
    lines = [
        "# Resultados humanos del pulido final",
        "",
        f"- Filas procesadas: {result['source']['rows']}",
        f"- SHA256 del CSV original: `{result['source']['sha256']}`",
        "- CSV modificado: no",
        "- Ganador: ninguno",
        "- Fase 6: abierta",
        "",
        "## Preferencias",
        "",
    ]
    for label, count in sorted(result["preferences"].items()):
        lines.append(f"- {label}: {count}")
    for group in GROUPS:
        data = result["groups"][group]
        lines.extend(["", f"## {group}", "", f"Muestras: {data['samples']}", "", "Medias:"])
        for field, value in data["average_scores"].items():
            lines.append(f"- {field}: {value:.3f}")
        lines.extend(["", "Notas humanas:"])
        lines.extend(f"- {note}" for note in data["human_notes"])
    lines.extend(["", "## Decisión", "", result["decision"]["reason"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or args.csv.parent
    output.mkdir(parents=True, exist_ok=True)
    result = summarize(args.csv)
    (output / "FINAL_POLISH_HUMAN_RESULTS.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "FINAL_POLISH_HUMAN_RESULTS.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
