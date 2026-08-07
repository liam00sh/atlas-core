from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .models import ProjectConfig, Sample
from .storage import atomic_write_text, serialize_csv, serialize_jsonl
from .validators import ValidationResult, sha256_file, validate_dataset


def export_dataset(config: ProjectConfig, samples: list[Sample], output_dir: Path, full_hash: bool = True) -> ValidationResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = validate_dataset(config, samples, full_hash=full_hash)
    atomic_write_text(output_dir / "metadata.csv", serialize_csv(samples))
    atomic_write_text(output_dir / "metadata.jsonl", serialize_jsonl(samples))
    tts = [s for s in samples if s.tts_usable and s.review_status in {"accepted", "accepted_with_notes"}]
    personality = [s for s in samples if s.personality_usable]
    atomic_write_text(output_dir / "tts_dataset.jsonl", serialize_jsonl(tts))
    atomic_write_text(output_dir / "personality_dataset.jsonl", serialize_jsonl(personality))
    pending = [s for s in samples if s.review_status in {"pending_review", "needs_second_review"}]
    atomic_write_text(output_dir / "review_queue.csv", serialize_csv(pending))
    metadata_hash = sha256_file(output_dir / "metadata.csv")
    manifest = {
        "schema_version": "2.0", "dataset_version": config.dataset_version,
        "tool_version": __version__, "generated_at": datetime.now(UTC).isoformat(),
        "file_count": len(samples), "total_duration_seconds": sum(s.duration_seconds for s in samples),
        "metadata_sha256": metadata_hash,
        "audio": [{"sample_id": s.sample_id, "relative_path": Path(s.relative_path).as_posix(), "sha256": s.sha256} for s in samples],
        "configuration": {"preset": config.preset, "dataset_type": config.dataset_type},
        "validation": validation.status,
    }
    atomic_write_text(output_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    atomic_write_text(output_dir / "DATASET_VALIDATION_REPORT.md", validation_report(config, samples, validation, metadata_hash))
    return validation


def validation_report(config: ProjectConfig, samples: list[Sample], result: ValidationResult, metadata_hash: str) -> str:
    status = Counter(s.review_status for s in samples)
    emotions = Counter(s.emotion for s in samples)
    intentions = Counter(s.intention for s in samples)
    quality = Counter(s.quality for s in samples)
    personality = Counter(tag for s in samples for tag in s.personality_tags)
    lines = [
        "# Atlas Dataset Studio — Informe de validación", "",
        f"- Versión del dataset: {config.dataset_version}",
        f"- Versión de la herramienta: {__version__}", f"- Muestras: {len(samples)}",
        f"- Duración: {sum(s.duration_seconds for s in samples):.3f} s",
        f"- Aceptadas: {status['accepted'] + status['accepted_with_notes']}",
        f"- Pendientes: {status['pending_review']}", f"- Excluidas: {status['excluded']}",
        f"- SHA-256 de metadatos: `{metadata_hash}`", "", f"## Resultado: {result.status}", "",
    ]
    for heading, counter in (("Expresiones", emotions), ("Intenciones", intentions), ("Personalidad", personality), ("Calidad", quality)):
        lines.extend((f"## {heading}", "", *(f"- {key}: {value}" for key, value in counter.most_common()), ""))
    lines.extend(("## Errores", "", *(f"- {item}" for item in result.errors or ["Ninguno"]), "", "## Advertencias", "", *(f"- {item}" for item in result.warnings or ["Ninguna"]), ""))
    if status["pending_review"] or result.errors:
        lines.append("El dataset no se declara oficialmente cerrado.")
    return "\n".join(lines) + "\n"
