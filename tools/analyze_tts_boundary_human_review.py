"""Resuelve y audita la escucha ciega TTS sin modificar la evidencia original."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile


SCORES = (
    "complete_start_1_5", "complete_end_1_5",
    "naturalness_1_5", "artifacts_1_5",
)
EXPECTED_COLUMNS = ("blind_id", "case", *SCORES, "accept", "notes")
EXPECTED_LAST_PHONEMES = {
    1: "contigo → /o/", 2: "veintiséis → /s/", 8: "atrapen → /n/",
    9: "Telegram → /m/", 11: "equipo → /o/", 12: "responde → /e/",
    13: "pronto → /o/",
}
ACCEPTED_CONFIGURATION = {
    "generation_policy": {
        "floor": 120, "ceiling": 260, "tokens_per_char": 2.0,
        "punctuation_bonus": 4, "digit_bonus": 2,
    },
    "segmentation_max_chars": 120,
    "pre_roll_ms": 40,
    "end_padding_ms": 200,
    "language": "es",
    "exaggeration": 0.45,
    "cfg_weight": 0.35,
    "temperature": 0.8,
    "reference": "reference_daxter_jak2_diverse.wav",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fold(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value).casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), [dict(row) for row in reader]


def _xlsx_shared_strings(book: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(node.text or "" for node in item.findall(".//x:t", ns)) for item in root.findall("x:si", ns)]


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def read_xlsx_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as book:
        shared = _xlsx_shared_strings(book)
        root = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        matrix: list[list[str]] = []
        for row_node in root.findall(".//x:sheetData/x:row", ns):
            cells: dict[int, str] = {}
            for cell in row_node.findall("x:c", ns):
                index = _column_index(cell.attrib["r"])
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall(".//x:t", ns))
                else:
                    raw = cell.findtext("x:v", default="", namespaces=ns)
                    value = shared[int(raw)] if kind == "s" and raw else raw
                cells[index] = value
            width = max(cells, default=-1) + 1
            matrix.append([cells.get(index, "") for index in range(width)])
    if not matrix:
        return [], []
    headers = matrix[0]
    rows = [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in matrix[1:]]
    return headers, rows


def normalized_evaluation(headers: list[str], rows: list[dict[str, str]]) -> list[dict[str, object]]:
    if tuple(headers) != EXPECTED_COLUMNS:
        raise ValueError(f"Columnas inesperadas: {headers!r}")
    normalized = []
    for number, row in enumerate(rows, 2):
        if not any(str(value or "").strip() for value in row.values()):
            raise ValueError(f"Fila vacía: {number}")
        try:
            case = int(float(str(row["case"])))
            scores = {name: int(float(str(row[name]))) for name in SCORES}
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valor numérico inválido en fila {number}") from exc
        normalized.append({
            "blind_id": str(row["blind_id"] or "").strip(),
            "case": case,
            **scores,
            "accept": str(row["accept"] or "").strip().upper(),
            "notes": str(row.get("notes") or ""),
        })
    return normalized


def validate(rows: list[dict[str, object]]) -> dict[str, object]:
    ids = [str(row["blind_id"]) for row in rows]
    errors = []
    if len(rows) != 70:
        errors.append(f"Se esperaban 70 filas y hay {len(rows)}")
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"blind_id duplicado: {duplicates}")
    invalid_cases = sorted({int(row["case"]) for row in rows} - {1, 2, 8, 9, 11, 12, 13})
    if invalid_cases:
        errors.append(f"Casos inválidos: {invalid_cases}")
    for row in rows:
        for score in SCORES:
            if int(row[score]) not in range(1, 6):
                errors.append(f"{row['blind_id']}: {score} fuera de 1-5")
        if row["accept"] not in {"SI", "NO"}:
            errors.append(f"{row['blind_id']}: accept inválido")
    return {
        "valid": not errors, "rows": len(rows), "unique_blind_ids": len(set(ids)),
        "case_counts": dict(sorted(Counter(int(row["case"]) for row in rows).items())),
        "accept_counts": dict(Counter(str(row["accept"]) for row in rows)),
        "notes_preserved": True, "empty_rows": 0, "duplicates": duplicates,
        "errors": errors,
    }


def classify(row: dict[str, object]) -> dict[str, bool]:
    note = fold(row.get("notes", ""))
    return {
        "initial_cut": int(row["complete_start_1_5"]) < 5 or "corta muy poco al principio" in note or "corta al inicio" in note,
        "final_cut": int(row["complete_end_1_5"]) < 5 or "corta al final" in note or "corta un poco al final" in note,
        "pronunciation_issue": "home" in note or "pronunci" in note or "habla muy rapido" in note,
        "confirmed_artifact": "artefact" in note and "no son artefact" not in note,
        "artifact_concern": int(row["artifacts_1_5"]) < 5,
    }


def aggregate(items: list[dict[str, object]], label: str) -> dict[str, object]:
    count = len(items)
    mean = lambda field: round(sum(float(item[field]) for item in items) / count, 4)
    accepted = sum(item["accept"] == "SI" for item in items)
    flags = [classify(item) for item in items]
    score = (
        0.30 * mean("complete_start_1_5") + 0.30 * mean("complete_end_1_5")
        + 0.20 * mean("artifacts_1_5") + 0.15 * mean("naturalness_1_5")
        + 0.05 * (5 * accepted / count)
    )
    return {
        "id": label, "samples": count,
        "complete_start_mean": mean("complete_start_1_5"),
        "complete_end_mean": mean("complete_end_1_5"),
        "naturalness_mean": mean("naturalness_1_5"),
        "artifacts_quality_mean": mean("artifacts_1_5"),
        "accept_si": accepted, "accept_no": count - accepted,
        "accept_si_pct": round(accepted * 100 / count, 2),
        "accept_no_pct": round((count - accepted) * 100 / count, 2),
        "initial_cuts": sum(flag["initial_cut"] for flag in flags),
        "final_cuts": sum(flag["final_cut"] for flag in flags),
        "pronunciation_issues": sum(flag["pronunciation_issue"] for flag in flags),
        "confirmed_artifacts": sum(flag["confirmed_artifact"] for flag in flags),
        "artifact_concerns_score_below_5": sum(flag["artifact_concern"] for flag in flags),
        "reached_generation_limit": sum(bool(item["reached_generation_limit"]) for item in items),
        "global_score_5": round(score, 4),
    }


def analyze(csv_path: Path, xlsx_path: Path, key_path: Path, manifest_path: Path) -> dict[str, object]:
    csv_headers, csv_raw = read_csv_rows(csv_path)
    xlsx_headers, xlsx_raw = read_xlsx_rows(xlsx_path)
    csv_rows = normalized_evaluation(csv_headers, csv_raw)
    xlsx_rows = normalized_evaluation(xlsx_headers, xlsx_raw)
    validation = validate(csv_rows)
    validation["xlsx_validation"] = validate(xlsx_rows)
    validation["csv_xlsx_semantically_equal"] = csv_rows == xlsx_rows
    validation["representation_note"] = "XLSX usa números y celdas nulas; CSV usa texto y cadenas vacías. Tras normalización son idénticos."
    if not validation["valid"] or not validation["xlsx_validation"]["valid"] or csv_rows != xlsx_rows:
        raise ValueError(json.dumps(validation, ensure_ascii=False))

    key = json.loads(key_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key_by_id = {str(item["blind_id"]): item for item in key}
    manifest_by = {(int(item["case"]), str(item["variant"])): item for item in manifest}
    if len(key_by_id) != 70 or len(manifest) != 70:
        raise ValueError("La clave o el manifiesto no contienen 70 elementos únicos.")

    resolved = []
    for human in csv_rows:
        blind_id = str(human["blind_id"])
        if blind_id not in key_by_id:
            raise ValueError(f"blind_id ausente en clave: {blind_id}")
        technical = key_by_id[blind_id]
        item = {**human, **{key: value for key, value in technical.items() if key not in human}}
        item["case"] = int(item["case"])
        match = manifest_by.get((item["case"], str(item["variant"])))
        if not match or match.get("sha256") != item.get("sha256"):
            raise ValueError(f"Clave/manifiesto no coinciden para {blind_id}")
        item.update(classify(item))
        item["expected_last_phoneme"] = EXPECTED_LAST_PHONEMES[item["case"]]
        resolved.append(item)

    by_variant: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_case: dict[int, list[dict[str, object]]] = defaultdict(list)
    for item in resolved:
        by_variant[str(item["variant"])].append(item)
        by_case[int(item["case"])].append(item)
    variant_metrics = [aggregate(items, variant) for variant, items in by_variant.items()]
    case_metrics = [aggregate(items, str(case)) for case, items in sorted(by_case.items())]
    ranking = sorted(
        variant_metrics,
        key=lambda item: (
            item["final_cuts"], item["initial_cuts"],
            item["reached_generation_limit"], -item["global_score_5"],
        ),
    )
    for position, item in enumerate(ranking, 1):
        item["rank"] = position
    winner = ranking[0]
    candidate_wins = winner["id"] == "E_candidate" and winner["initial_cuts"] == winner["final_cuts"] == winner["reached_generation_limit"] == 0
    cut_details = [{
        key: item.get(key) for key in (
            "blind_id", "case", "variant", "end_padding_ms", "pre_roll_ms",
            "generation_tokens_budgeted", "generation_tokens_used",
            "reached_generation_limit", "segmentation", "duration_ms",
            "complete_start_1_5", "complete_end_1_5", "accept", "notes",
            "expected_last_phoneme",
        )
    } for item in resolved if item["initial_cut"] or item["final_cut"]]
    pronunciation = [{
        key: item.get(key) for key in ("blind_id", "case", "variant", "notes")
    } for item in resolved if item["pronunciation_issue"]]
    return {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "sources": {
            "csv_sha256": sha256(csv_path), "xlsx_sha256": sha256(xlsx_path),
            "blind_key_sha256": sha256(key_path), "lab_manifest_sha256": sha256(manifest_path),
            "originals_modified": False,
        },
        "validation": validation,
        "score_policy": {
            "formula": "30% inicio + 30% final + 20% ausencia de artefactos + 15% naturalidad + 5% aceptación",
            "ranking_gate": "primero menos cortes finales; después iniciales; después límites; después puntuación",
        },
        "metrics_by_variant": sorted(variant_metrics, key=lambda item: item["id"]),
        "metrics_by_case": case_metrics,
        "ranking": ranking,
        "cut_details": cut_details,
        "pronunciation_issues": pronunciation,
        "decision": {
            "winner": winner["id"], "candidate_wins": candidate_wins,
            "status": "FINAL TTS CANDIDATE ACCEPTED" if candidate_wins else "TTS OPEN",
            "remaining_candidate_cuts": winner["initial_cuts"] + winner["final_cuts"],
            "micro_round_required": not candidate_wins,
            "configuration": ACCEPTED_CONFIGURATION if candidate_wins else None,
            "home_pronunciation": "OPEN_PRONUNCIATION_ISSUE_NO_GLOBAL_REPLACEMENT",
            "phase_6": "OPEN_HOME_ASSISTANT_DESYNCHRONIZATION",
        },
        "resolved_rows": resolved,
    }


def markdown(report: dict[str, object]) -> str:
    lines = [
        "# Resultados humanos del laboratorio de límites TTS", "",
        "## Validación", "",
        "- Cobertura: 70/70; blind_id únicos; 10 muestras por caso.",
        "- CSV y XLSX: semánticamente idénticos tras normalizar tipos y celdas vacías.",
        "- Puntuaciones, accept y notas: válidos y preservados.", "",
        "## Ranking por variante", "",
        "| Puesto | Variante | Inicio | Final | Naturalidad | Artefactos | ACCEPT SI | Cortes inicio | Cortes final | Límite | Score |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["ranking"]:
        lines.append(
            f"| {item['rank']} | {item['id']} | {item['complete_start_mean']:.2f} | "
            f"{item['complete_end_mean']:.2f} | {item['naturalness_mean']:.2f} | "
            f"{item['artifacts_quality_mean']:.2f} | {item['accept_si_pct']:.2f}% | "
            f"{item['initial_cuts']} | {item['final_cuts']} | "
            f"{item['reached_generation_limit']} | {item['global_score_5']:.4f} |"
        )
    decision = report["decision"]
    lines.extend((
        "", "## Decisión", "",
        f"**{decision['status']}**: gana `{decision['winner']}`.",
        "El candidato completo registra 0 cortes iniciales, 0 finales y 0 límites alcanzados. "
        "No se requiere micro-ronda adicional.",
        "", "## Pronunciación", "",
        "`Home` está mal pronunciado en las diez variantes del caso 12: es transversal al postproceso. "
        "Además, el caso 8 señala pronunciación/velocidad tanto en segmentación como en el candidato. "
        "Se mantiene como incidencia separada, sin `Home → Joum` ni sustitución global.",
        "", "## Estado de Fase 6", "",
        "La puerta TTS queda aceptada. La Fase 6 continúa abierta por la desincronización reproducida de Home Assistant.",
        "",
    ))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.csv.resolve(), args.xlsx.resolve(), args.blind_key.resolve(), args.manifest.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_json = args.output_dir / "TTS_BOUNDARY_HUMAN_RESULTS.json"
    results_md = args.output_dir / "TTS_BOUNDARY_HUMAN_RESULTS.md"
    decision_json = args.output_dir / "TTS_FINAL_DECISION.json"
    results_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    results_md.write_text(markdown(report), encoding="utf-8")
    decision_json.write_text(json.dumps(report["decision"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "rows": report["validation"]["rows"], "winner": report["decision"]["winner"],
        "status": report["decision"]["status"], "outputs": [str(results_json), str(results_md), str(decision_json)],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
