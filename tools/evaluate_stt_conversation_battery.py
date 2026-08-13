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
    normalized_errors = sum(distance(words(row["expected_text"]), words(row["normalized_transcript"])) for row in measured)
    def rate(expected, observed):
        return round(sum(expected(row) == observed(row) for row in measured) / len(measured), 4) if measured else None
    report = {
        "schema_version": 1,
        "total_cases": len(rows),
        "measured_cases": len(measured),
        "coverage": round(len(measured) / len(rows), 4) if rows else 0.0,
        "exact_match": rate(lambda r: words(r["expected_text"]), lambda r: words(r["raw_transcript"])),
        "wer": round(errors / word_total, 4) if word_total else None,
        "normalized_wer": round(normalized_errors / word_total, 4) if word_total else None,
        "intent_accuracy": rate(lambda r: r["expected_intent"], lambda r: r["observed_intent"]),
        "entity_accuracy": rate(lambda r: r["expected_entity"], lambda r: r["observed_entity"]),
        "command_accuracy": rate(lambda r: _bool(r["command_expected"]), lambda r: _bool(r["command_observed"])),
        "safe_action_accuracy": rate(lambda r: _bool(r["safe_action_expected"]), lambda r: _bool(r["safe_action_observed"])),
        "valid_for_release_claim": len(measured) == len(rows),
    }
    report["by_category"] = {
        category: evaluate_category([row for row in rows if row.get("category") == category])
        for category in sorted({row.get("category", "") for row in rows})
    }
    return report


def evaluate_category(rows: list[dict]) -> dict:
    measured = [row for row in rows if str(row.get("raw_transcript", "")).strip()]
    word_total = sum(len(words(row["expected_text"])) for row in measured)
    raw_errors = sum(distance(words(row["expected_text"]), words(row["raw_transcript"])) for row in measured)
    normalized_errors = sum(distance(words(row["expected_text"]), words(row["normalized_transcript"])) for row in measured)
    def rate(field_expected, field_observed, *, boolean=False):
        if not measured:
            return None
        transform = _bool if boolean else lambda value: str(value).strip().casefold()
        return round(sum(transform(row[field_expected]) == transform(row[field_observed]) for row in measured) / len(measured), 4)
    return {
        "total_cases": len(rows), "measured_cases": len(measured),
        "wer": round(raw_errors / word_total, 4) if word_total else None,
        "normalized_wer": round(normalized_errors / word_total, 4) if word_total else None,
        "intent_accuracy": rate("expected_intent", "observed_intent"),
        "entity_accuracy": rate("expected_entity", "observed_entity"),
        "command_accuracy": rate("command_expected", "command_observed", boolean=True),
        "safe_action_accuracy": rate("safe_action_expected", "safe_action_observed", boolean=True),
    }


def error_rows(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        if not str(row.get("raw_transcript", "")).strip():
            continue
        checks = {
            "raw_text": words(row["expected_text"]) == words(row["raw_transcript"]),
            "normalized_text": words(row["expected_text"]) == words(row["normalized_transcript"]),
            "intent": str(row["expected_intent"]).casefold() == str(row["observed_intent"]).casefold(),
            "entity": str(row["expected_entity"]).casefold() == str(row["observed_entity"]).casefold(),
            "command": _bool(row["command_expected"]) == _bool(row["command_observed"]),
            "safe_action": _bool(row["safe_action_expected"]) == _bool(row["safe_action_observed"]),
        }
        failures = [name for name, passed in checks.items() if not passed]
        if failures:
            result.append({**row, "error_groups": "|".join(failures)})
    return result


def write_reports(rows: list[dict], output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate(rows)
    (output_dir / "STT_HUMAN_RESULTS.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = error_rows(rows)
    fields = list(rows[0].keys()) + (["error_groups"] if rows else [])
    with (output_dir / "STT_HUMAN_ERRORS.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(failures)
    lines = [
        "# Resultados humanos STT", "", f"Cobertura: {report['measured_cases']}/{report['total_cases']}",
        f"Válido para afirmar resultado final: {'sí' if report['valid_for_release_claim'] else 'no'}", "",
        "Las métricas no grabadas permanecen nulas y no cuentan como aciertos.", "", "## Por categoría", "",
    ]
    for category, data in report["by_category"].items():
        lines.append(f"- {category}: {data['measured_cases']}/{data['total_cases']}; intent={data['intent_accuracy']}; entidad={data['entity_accuracy']}; WER normalizado={data['normalized_wer']}")
    (output_dir / "STT_HUMAN_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args()
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        report = evaluate(rows)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_dir:
        write_reports(rows, args.report_dir)
    return 0 if report["valid_for_release_claim"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
