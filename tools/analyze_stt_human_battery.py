"""Auditoría funcional de una batería STT completa, sin tocar sus fuentes."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unicodedata
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_stt_conversation_battery import distance, evaluate, words
from tools.run_stt_human_battery import inspect_router_only


NUMBER_WORDS = {
    "uno": "1", "una": "1", "dos": "2", "dieciocho": "18", "veinte": "20", "treinta": "30",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_tokens(value: str) -> list[str]:
    value = re.sub(r"(?<=[a-záéíóúüñ])(?=[A-ZÁÉÍÓÚÜÑ])", " ", str(value))
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", value)
    tokens = re.findall(r"[a-z0-9]+", value)
    return [NUMBER_WORDS.get(token, token) for token in tokens]


def classify_row(row: dict) -> dict:
    expected = words(row["expected_text"])
    raw = words(row["raw_transcript"])
    surface_equivalent = expected == raw
    semantic_equivalent = semantic_tokens(row["expected_text"]) == semantic_tokens(row["raw_transcript"])
    intent_ok = row["expected_intent"].casefold() == row["observed_intent"].casefold()
    entity_ok = row["expected_entity"].casefold() == row["observed_entity"].casefold()
    if surface_equivalent:
        stt_class = "exact_or_surface_equivalent"
    elif semantic_equivalent:
        stt_class = "minor_format_number_or_tokenization"
    elif intent_ok:
        stt_class = "lexical_error_intent_preserved"
    else:
        stt_class = "stt_error_changes_intent"
    if intent_ok and entity_ok:
        functional_class = "correct"
    elif semantic_equivalent or surface_equivalent:
        functional_class = "normalization_or_router_error"
    else:
        functional_class = "joint_stt_router_error"
    replay = inspect_router_only(row["normalized_transcript"])
    return {
        "case_id": int(row["id"]), "category": row["category"],
        "expected_text": row["expected_text"], "raw_transcript": row["raw_transcript"],
        "normalized_transcript": row["normalized_transcript"],
        "expected_intent": row["expected_intent"], "observed_intent": row["observed_intent"],
        "expected_entity": row["expected_entity"], "observed_entity": row["observed_entity"],
        "stt_class": stt_class, "functional_class": functional_class,
        "semantic_or_functionally_equivalent": semantic_equivalent or surface_equivalent or intent_ok,
        "intent_correct": intent_ok, "entity_correct": entity_ok,
        "router_replay_intent": replay.intent, "router_replay_entity": replay.entity,
        "router_replay_correct": replay.intent == row["expected_intent"] and replay.entity.casefold() == row["expected_entity"].casefold(),
    }


def analyze(rows: list[dict], *, audio_dir: Path | None = None) -> dict:
    if len(rows) != 160 or any(row.get("status") != "evaluated" for row in rows):
        raise ValueError("La auditoría final exige exactamente 160 casos evaluados.")
    classified = [classify_row(row) for row in rows]
    automatic = evaluate(rows)
    retry_files = sorted(audio_dir.glob("*.previous-*.wav")) if audio_dir else []
    retry_cases = sorted({int(re.search(r"stt_(\d{3})", path.name).group(1)) for path in retry_files})
    counts = Counter(item["stt_class"] for item in classified)
    functional = Counter(item["functional_class"] for item in classified)
    semantic_correct = sum(item["semantic_or_functionally_equivalent"] for item in classified)
    joint_correct = sum(item["semantic_or_functionally_equivalent"] and item["intent_correct"] and item["entity_correct"] for item in classified)
    replay_correct = sum(item["router_replay_correct"] for item in classified)
    by_category = {}
    for category in sorted({item["category"] for item in classified}):
        items = [item for item in classified if item["category"] == category]
        by_category[category] = {
            "cases": len(items),
            "surface_equivalent": sum(item["stt_class"] == "exact_or_surface_equivalent" for item in items),
            "semantic_or_functionally_equivalent": sum(item["semantic_or_functionally_equivalent"] for item in items),
            "intent_correct": sum(item["intent_correct"] for item in items),
            "entity_correct": sum(item["entity_correct"] for item in items),
            "joint_correct": sum(item["semantic_or_functionally_equivalent"] and item["intent_correct"] and item["entity_correct"] for item in items),
            "router_replay_correct": sum(item["router_replay_correct"] for item in items),
            "wer": automatic["by_category"][category]["wer"],
        }
    char_expected = [list(" ".join(words(row["expected_text"]))) for row in rows]
    char_raw = [list(" ".join(words(row["raw_transcript"]))) for row in rows]
    char_total = sum(len(item) for item in char_expected)
    cer_errors = sum(distance(left, right) for left, right in zip(char_expected, char_raw))
    return {
        "schema_version": 1,
        "coverage": {"evaluated": 160, "total": 160, "ratio": 1.0},
        "metrics": {
            "surface_equivalent_accuracy": round(counts["exact_or_surface_equivalent"] / 160, 4),
            "semantic_functional_stt_accuracy": round(semantic_correct / 160, 4),
            "intent_accuracy_observed": automatic["intent_accuracy"],
            "entity_accuracy_observed": automatic["entity_accuracy"],
            "joint_stt_intent_entity_accuracy_observed": round(joint_correct / 160, 4),
            "router_replay_accuracy_after_general_fixes": round(replay_correct / 160, 4),
            "wer": automatic["wer"], "cer": round(cer_errors / char_total, 4),
        },
        "classification_counts": dict(sorted(counts.items())),
        "functional_error_counts": dict(sorted(functional.items())),
        "retry_evidence": {"cases_with_previous_takes": len(retry_cases), "discarded_takes": len(retry_files), "case_ids": retry_cases},
        "by_category": by_category,
        "technical_vocabulary": {
            "ollama_final_failures": [item["case_id"] for item in classified if item["expected_entity"] == "Ollama" and not item["intent_correct"]],
            "global_automatic_substitution_added": False,
            "reason": "Oyama/Ojima/O llama pueden ser lenguaje real fuera de un contexto inequívoco; se conserva repetición o aclaración.",
        },
        "cases": classified,
        "phase_6_closed": False,
    }


def markdown(report: dict) -> str:
    m, c, f = report["metrics"], report["classification_counts"], report["functional_error_counts"]
    lines = [
        "# Auditoría humana STT 160/160", "", "Cobertura: **160/160**.", "",
        "## Métricas finales", "",
        f"- Equivalencia superficial: {m['surface_equivalent_accuracy']:.2%}.",
        f"- Exactitud STT semántica/funcional: {m['semantic_functional_stt_accuracy']:.2%}.",
        f"- Exactitud de intent observada: {m['intent_accuracy_observed']:.2%}.",
        f"- Exactitud de entidad observada: {m['entity_accuracy_observed']:.2%}.",
        f"- Exactitud conjunta STT + intent + entidad observada: {m['joint_stt_intent_entity_accuracy_observed']:.2%}.",
        f"- WER: {m['wer']:.2%}; CER: {m['cer']:.2%}.", "",
        "## Clasificación STT", "",
        f"- Exacto/equivalente superficial: {c.get('exact_or_surface_equivalent', 0)}.",
        f"- Diferencia menor de formato, número o tokenización: {c.get('minor_format_number_or_tokenization', 0)}.",
        f"- Error léxico con intención conservada: {c.get('lexical_error_intent_preserved', 0)}.",
        f"- Error STT que cambia intención: {c.get('stt_error_changes_intent', 0)}.", "",
        "## Fallos funcionales observados", "",
        f"- Correctos: {f.get('correct', 0)}.",
        f"- Normalización/router con STT semánticamente adecuado: {f.get('normalization_or_router_error', 0)}.",
        f"- Error conjunto STT + router: {f.get('joint_stt_router_error', 0)}.", "",
        "## Por categoría", "", "| Categoría | Casos | STT semántico | Intent | Conjunto | Replay corregido | WER |", "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for category, item in report["by_category"].items():
        lines.append(f"| {category} | {item['cases']} | {item['semantic_or_functionally_equivalent']}/20 | {item['intent_correct']}/20 | {item['joint_correct']}/20 | {item['router_replay_correct']}/20 | {item['wer']:.2%} |")
    lines += [
        "", "## Evidencia de repeticiones", "",
        f"Se conservaron {report['retry_evidence']['discarded_takes']} tomas descartadas correspondientes a {report['retry_evidence']['cases_with_previous_takes']} casos.", "",
        "## Recomendación", "",
        "Se corrigen reglas generales de puntuación, sufijos conversacionales y equivalencia de identificadores numéricos. No se añade una sustitución global Oyama/Ojima→Ollama: sería ambigua fuera del contexto de infraestructura.", "",
        "Fase 6 permanece abierta hasta repetir la E2E real reparada.", "",
    ]
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    source_hash = _sha256(args.input)
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report = analyze(rows, audio_dir=args.audio_dir)
    report["source"] = {"file": args.input.name, "sha256": source_hash, "modified": False}
    _atomic_write(args.output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(args.output_md, markdown(report))
    if _sha256(args.input) != source_hash:
        raise RuntimeError("La fuente STT cambió durante la auditoría.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
