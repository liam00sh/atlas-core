"""Calcula métricas sin convertir filas sin audio/transcripción en aciertos."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path


def words(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", value)


def distance(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for i, source in enumerate(left, 1):
        new = [i]
        for j, target in enumerate(right, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (source != target)))
        row = new
    return row[-1]


def _bool(value: str) -> bool:
    return str(value).strip().casefold() in {"1", "true", "yes", "si", "sí"}


def evaluate(rows: list[dict]) -> dict:
    measured = [row for row in rows if str(row.get("raw_transcript", "")).strip()]
    word_total = sum(len(words(row["expected_text"])) for row in measured)
    errors = sum(distance(words(row["expected_text"]), words(row["raw_transcript"])) for row in measured)
    def rate(expected, observed):
        return round(sum(expected(row) == observed(row) for row in measured) / len(measured), 4) if measured else None
    return {
        "schema_version": 1,
        "total_cases": len(rows),
        "measured_cases": len(measured),
        "coverage": round(len(measured) / len(rows), 4) if rows else 0.0,
        "exact_match": rate(lambda r: words(r["expected_text"]), lambda r: words(r["raw_transcript"])),
        "wer": round(errors / word_total, 4) if word_total else None,
        "intent_accuracy": rate(lambda r: r["expected_intent"], lambda r: r["observed_intent"]),
        "entity_accuracy": rate(lambda r: r["expected_entity"], lambda r: r["observed_entity"]),
        "command_accuracy": rate(lambda r: _bool(r["command_expected"]), lambda r: _bool(r["command_observed"])),
        "safe_action_accuracy": rate(lambda r: _bool(r["safe_action_expected"]), lambda r: _bool(r["safe_action_observed"])),
        "valid_for_release_claim": len(measured) == len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        report = evaluate(list(csv.DictReader(handle)))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["valid_for_release_claim"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
