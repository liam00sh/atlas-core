"""Prepara manifests trazables para adaptar Chatterbox sin tocar el maestro.

El proyecto oficial de Chatterbox no publica un pipeline estable de fine-tuning.
Estos manifests conservan todas las columnas humanas y separan los clips aptos,
los excluidos y los que necesitan revisión antes de cualquier entrenamiento.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path


PREP_FIELDS = (
    "training_status", "split", "training_audio_path", "selection_reasons",
    "similar_text_group", "split_seed",
)
SPLIT_RATIOS = {"train": 0.8, "validation": 0.1, "test": 0.1}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


class UnionFind:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def text_groups(rows: list[dict[str, str]], threshold: float = 0.9) -> dict[str, str]:
    """Agrupa textos iguales o casi iguales para impedir fuga entre splits."""
    ids = [row["sample_id"] for row in rows]
    union = UnionFind(ids)
    normalized = {row["sample_id"]: canonical_text(row.get("normalized_text") or row["text"]) for row in rows}
    exact: dict[str, list[str]] = defaultdict(list)
    trigram_index: dict[str, set[str]] = defaultdict(set)
    trigrams: dict[str, set[str]] = {}
    for sample_id, text in normalized.items():
        exact[text].append(sample_id)
        padded = f"  {text}  "
        grams = {padded[i:i + 3] for i in range(max(1, len(padded) - 2))}
        trigrams[sample_id] = grams
        for gram in grams:
            trigram_index[gram].add(sample_id)
    for members in exact.values():
        for member in members[1:]:
            union.union(members[0], member)
    seen: set[tuple[str, str]] = set()
    for sample_id in ids:
        candidates: set[str] = set()
        for gram in trigrams[sample_id]:
            candidates.update(trigram_index[gram])
        left_text = normalized[sample_id]
        for other in candidates:
            pair = tuple(sorted((sample_id, other)))
            if sample_id == other or pair in seen:
                continue
            seen.add(pair)
            right_text = normalized[other]
            if not left_text or not right_text:
                continue
            length_ratio = min(len(left_text), len(right_text)) / max(len(left_text), len(right_text))
            if length_ratio < 0.78:
                continue
            intersection = len(trigrams[sample_id] & trigrams[other])
            gram_union = len(trigrams[sample_id] | trigrams[other])
            if gram_union and intersection / gram_union < 0.62:
                continue
            if SequenceMatcher(None, left_text, right_text).ratio() >= threshold:
                union.union(sample_id, other)
    grouped: dict[str, list[str]] = defaultdict(list)
    for sample_id in ids:
        grouped[union.find(sample_id)].append(sample_id)
    result = {}
    for index, members in enumerate(sorted(grouped.values(), key=lambda x: min(x)), 1):
        group_id = f"text_{index:04d}"
        for sample_id in members:
            result[sample_id] = group_id
    return result


def classify(row: dict[str, str], audit: dict[str, str]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if audit.get("severity") == "ERROR" or audit.get("readable", "").casefold() != "true":
        reasons.append(f"audit_error:{audit.get('issues') or 'unreadable'}")
    if audit.get("metadata_sha256_match", "").casefold() != "true":
        reasons.append("metadata_sha256_mismatch")
    if row.get("tts_usable", "").casefold() not in {"true", "1", "yes", "si", "sí"}:
        reasons.append("tts_usable_false")
    if row.get("quality", "").casefold() == "limite":
        reasons.append("quality_limite")
    if reasons:
        return "excluded", reasons

    if audit.get("severity") in {"REVIEW", "WARNING"}:
        reasons.append(f"audit_{audit['severity'].casefold()}:{audit.get('issues') or 'unspecified'}")
    if row.get("quality", "").casefold() == "aceptable":
        reasons.append("quality_aceptable")
    duration = float(audit.get("duration_seconds") or row.get("duration_seconds") or 0)
    if duration < 0.75:
        reasons.append("duration_under_0_75s")
    if reasons:
        return "review", reasons
    return "included", ["audit_info;quality_buena;duration_training_range"]


def assign_splits(rows: list[dict[str, str]], groups: dict[str, str], seed: int) -> dict[str, str]:
    by_group: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_group[groups[row["sample_id"]]].append(row["sample_id"])
    rng = random.Random(seed)
    units = list(by_group.items())
    rng.shuffle(units)
    units.sort(key=lambda item: len(item[1]), reverse=True)
    total = len(rows)
    targets = {name: ratio * total for name, ratio in SPLIT_RATIOS.items()}
    counts = Counter()
    assignments: dict[str, str] = {}
    for _, sample_ids in units:
        split = max(SPLIT_RATIOS, key=lambda name: (targets[name] - counts[name]) / SPLIT_RATIOS[name])
        for sample_id in sample_ids:
            assignments[sample_id] = split
        counts[split] += len(sample_ids)
    return assignments


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()

    metadata = args.metadata.resolve()
    audit_path = args.audit.resolve()
    audio_root = args.audio_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata_hash = sha256_file(metadata)
    if metadata_hash != args.expected_metadata_sha256.casefold():
        raise SystemExit(f"Hash maestro inesperado: {metadata_hash}")
    with metadata.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        metadata_fields = reader.fieldnames or []
        rows = list(reader)
    with audit_path.open(encoding="utf-8-sig", newline="") as handle:
        audits = {row["sample_id"]: row for row in csv.DictReader(handle)}
    if len(rows) != 1300 or set(audits) != {row["sample_id"] for row in rows}:
        raise SystemExit("El maestro o la auditoría no contienen exactamente las mismas 1.300 muestras")
    for row in rows:
        path = audio_root / (row.get("relative_path") or row["audio_file"])
        if not path.is_file() or sha256_file(path) != row["sha256"].casefold():
            raise SystemExit(f"WAV ausente o alterado: {row['sample_id']}")

    groups = text_groups(rows)
    classified: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        status, reasons = classify(row, audits[row["sample_id"]])
        prepared = dict(row)
        prepared.update({
            "training_status": status,
            "split": "",
            "training_audio_path": (Path(os.path.relpath(audio_root / (row.get("relative_path") or row["audio_file"]), output))).as_posix(),
            "selection_reasons": ";".join(reasons),
            "similar_text_group": groups[row["sample_id"]],
            "split_seed": str(args.seed),
        })
        classified[status].append(prepared)
    assignments = assign_splits(classified["included"], groups, args.seed)
    for row in classified["included"]:
        row["split"] = assignments[row["sample_id"]]

    output_fields = list(metadata_fields) + list(PREP_FIELDS)
    filenames = {
        "included": "TTS_TRAINING_INCLUDED.csv",
        "excluded": "TTS_TRAINING_EXCLUDED.csv",
        "review": "TTS_TRAINING_REVIEW.csv",
    }
    for status, filename in filenames.items():
        write_csv(output / filename, classified[status], output_fields)
    for split in SPLIT_RATIOS:
        split_rows = [row for row in classified["included"] if row["split"] == split]
        write_csv(output / f"{split}.csv", split_rows, output_fields)
        with (output / f"{split}.txt").open("w", encoding="utf-8", newline="\n") as handle:
            for row in split_rows:
                handle.write(f"{row['training_audio_path']}|{row['text']}|{row['normalized_text']}\n")

    split_stats = {}
    for split in SPLIT_RATIOS:
        subset = [row for row in classified["included"] if row["split"] == split]
        split_stats[split] = {
            "samples": len(subset),
            "seconds": round(sum(float(row["duration_seconds"]) for row in subset), 4),
            "minutes": round(sum(float(row["duration_seconds"]) for row in subset) / 60, 4),
            "games": dict(sorted(Counter(row["source_game"] for row in subset).items())),
            "emotions": dict(sorted(Counter(row["emotion"] for row in subset).items())),
        }
    group_splits: dict[str, set[str]] = defaultdict(set)
    for row in classified["included"]:
        group_splits[row["similar_text_group"]].add(row["split"])
    leaking = {group: sorted(splits) for group, splits in group_splits.items() if len(splits) > 1}
    stats = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "metadata_sha256": metadata_hash,
        "seed": args.seed,
        "source_samples": len(rows),
        "included": len(classified["included"]),
        "excluded": len(classified["excluded"]),
        "review": len(classified["review"]),
        "splits": split_stats,
        "similar_text_groups": len(set(groups.values())),
        "cross_split_similar_text_leaks": leaking,
        "official_training_pipeline": False,
        "format_note": "Manifest portable; Chatterbox 0.1.7 no publica un cargador o pipeline oficial de fine-tuning.",
    }
    (output / "TTS_TRAINING_SPLITS.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Preparación del dataset para Chatterbox Multilingual V2", "",
        f"- Maestro: `{metadata.name}` ({metadata_hash})", f"- Seed: `{args.seed}`",
        f"- Incluidas: {stats['included']}", f"- Revisión separada: {stats['review']}",
        f"- Excluidas: {stats['excluded']}", "", "## Splits", "",
        "| Split | Muestras | Minutos |", "|---|---:|---:|",
    ]
    for split, values in split_stats.items():
        lines.append(f"| {split} | {values['samples']} | {values['minutes']} |")
    lines += [
        "", "Los grupos de texto igual o casi igual se asignan completos a un único split.",
        f"Fugas detectadas entre splits: {len(leaking)}.", "",
        "`review` no participa en los splits: conserva clips cortos, calidad aceptable o avisos de auditoría para decisión explícita posterior.",
        "`excluded` conserva el registro y motivo; ningún WAV ni texto humano se modifica.",
    ]
    (output / "TTS_TRAINING_DATASET_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    hash_targets = [output / name for name in filenames.values()]
    hash_targets += [output / f"{split}{suffix}" for split in SPLIT_RATIOS for suffix in (".csv", ".txt")]
    hash_targets += [output / "TTS_TRAINING_SPLITS.json", output / "TTS_TRAINING_DATASET_REPORT.md"]
    (output / "SHA256SUMS.txt").write_text("".join(f"{sha256_file(path)}  {path.name}\n" for path in hash_targets), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0 if not leaking else 2


if __name__ == "__main__":
    raise SystemExit(main())
