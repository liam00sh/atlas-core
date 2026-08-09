"""Auditoría reproducible y no destructiva del dataset final de Daxter.

La herramienta valida el CSV maestro contra WAV PCM, calcula métricas técnicas,
genera estadísticas y crea una copia inmutable del CSV. No modifica el audio ni
las columnas humanas de texto o clasificación.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import struct
import sys
import wave
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


EXPECTED_COLUMNS = {"sample_id", "audio_file", "relative_path", "text", "normalized_text", "sha256"}
CATEGORICAL_FIELDS = (
    "source_game", "emotion", "intention", "energy", "emotion_intensity",
    "quality", "personality_usable", "personality_strength",
    "conversation_use", "tts_usable", "review_status", "audit_status",
)
FULL_FIELDS = (
    "sample_id", "audio_file", "source_game", "readable", "severity", "issues",
    "sample_rate", "channels", "sample_width_bits", "duration_seconds",
    "leading_silence_seconds", "trailing_silence_seconds", "silence_percent",
    "rms_dbfs", "peak_dbfs", "clipping_percent", "dc_offset",
    "nearly_empty", "file_sha256", "metadata_sha256_match", "pcm_sha256",
    "acoustic_fingerprint", "exact_duplicate_group", "acoustic_duplicate_group",
)


@dataclass
class AudioMetrics:
    sample_id: str
    audio_file: str
    source_game: str
    readable: bool = False
    severity: str = "ERROR"
    issues: str = ""
    sample_rate: int | str = ""
    channels: int | str = ""
    sample_width_bits: int | str = ""
    duration_seconds: float | str = ""
    leading_silence_seconds: float | str = ""
    trailing_silence_seconds: float | str = ""
    silence_percent: float | str = ""
    rms_dbfs: float | str = ""
    peak_dbfs: float | str = ""
    clipping_percent: float | str = ""
    dc_offset: float | str = ""
    nearly_empty: bool | str = ""
    file_sha256: str = ""
    metadata_sha256_match: bool | str = ""
    pcm_sha256: str = ""
    acoustic_fingerprint: str = ""
    exact_duplicate_group: str = ""
    acoustic_duplicate_group: str = ""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def dbfs(value: float) -> float:
    return round(20.0 * math.log10(max(value, 1e-12)), 3)


def _decode_pcm(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [value - 128 for value in raw]
    if sample_width == 2:
        values = array("h")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        return list(values)
    if sample_width == 3:
        values = []
        for offset in range(0, len(raw), 3):
            block = raw[offset:offset + 3]
            if len(block) < 3:
                break
            unsigned = block[0] | (block[1] << 8) | (block[2] << 16)
            values.append(unsigned - (1 << 24) if unsigned & (1 << 23) else unsigned)
        return values
    if sample_width == 4:
        count = len(raw) // 4
        return list(struct.unpack(f"<{count}i", raw[:count * 4]))
    raise ValueError(f"profundidad PCM no soportada: {sample_width * 8} bits")


def _mono_samples(samples: list[int], channels: int) -> list[float]:
    if channels == 1:
        return [float(value) for value in samples]
    usable = len(samples) - (len(samples) % channels)
    return [sum(samples[i:i + channels]) / channels for i in range(0, usable, channels)]


def _edge_silence(mono: list[float], threshold: float, sample_rate: int) -> tuple[float, float]:
    leading = 0
    for value in mono:
        if abs(value) > threshold:
            break
        leading += 1
    trailing = 0
    for value in reversed(mono):
        if abs(value) > threshold:
            break
        trailing += 1
    return round(leading / sample_rate, 4), round(trailing / sample_rate, 4)


def _acoustic_fingerprint(mono: list[float], sample_rate: int, peak: float) -> str:
    """Hash conservador de la envolvente; coincidencias se marcan REVIEW, no se eliminan."""
    window = max(1, sample_rate // 20)  # 50 ms
    envelope: list[float] = []
    for start in range(0, len(mono), window):
        chunk = mono[start:start + window]
        if chunk:
            envelope.append(math.sqrt(sum(x * x for x in chunk) / len(chunk)) / max(peak, 1.0))
    if not envelope:
        return ""
    quantized = bytes(min(31, int(round(value * 31))) for value in envelope)
    duration_bucket = round(len(mono) / sample_rate, 2)
    return hashlib.sha256(f"{duration_bucket:.2f}|".encode() + quantized).hexdigest()


def audit_wav(row: dict[str, str], audio_root: Path) -> AudioMetrics:
    result = AudioMetrics(row["sample_id"], row["audio_file"], row.get("source_game", ""))
    path = audio_root / row.get("relative_path", row["audio_file"])
    issues: list[str] = []
    if not path.is_file():
        result.issues = "missing_audio"
        return result
    try:
        result.file_sha256 = sha256_file(path)
        result.metadata_sha256_match = result.file_sha256.lower() == row.get("sha256", "").lower()
        if not result.metadata_sha256_match:
            issues.append("sha256_mismatch")
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            compression = wav.getcomptype()
            raw = wav.readframes(frame_count)
        if compression != "NONE":
            raise ValueError(f"compresión WAV no soportada: {compression}")
        samples = _decode_pcm(raw, sample_width)
        mono = _mono_samples(samples, channels)
        full_scale = float((1 << (sample_width * 8 - 1)) - 1)
        peak_abs = max((abs(x) for x in mono), default=0.0)
        rms = math.sqrt(sum(x * x for x in mono) / len(mono)) if mono else 0.0
        threshold = full_scale * (10 ** (-40 / 20))
        leading, trailing = _edge_silence(mono, threshold, sample_rate)
        clipped = sum(abs(x) >= full_scale * 0.999 for x in mono)
        silent = sum(abs(x) <= threshold for x in mono)

        result.readable = True
        result.sample_rate = sample_rate
        result.channels = channels
        result.sample_width_bits = sample_width * 8
        result.duration_seconds = round(frame_count / sample_rate, 4)
        result.leading_silence_seconds = leading
        result.trailing_silence_seconds = trailing
        result.silence_percent = round(100 * silent / max(1, len(mono)), 3)
        result.rms_dbfs = dbfs(rms / full_scale)
        result.peak_dbfs = dbfs(peak_abs / full_scale)
        result.clipping_percent = round(100 * clipped / max(1, len(mono)), 5)
        result.dc_offset = round((sum(mono) / max(1, len(mono))) / full_scale, 7)
        result.nearly_empty = result.rms_dbfs < -50.0
        result.pcm_sha256 = hashlib.sha256(raw).hexdigest()
        result.acoustic_fingerprint = _acoustic_fingerprint(mono, sample_rate, peak_abs)

        expected = {
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width_bits": sample_width * 8,
        }
        for key, actual in expected.items():
            recorded = row.get(key, "").strip()
            if recorded and int(float(recorded)) != actual:
                issues.append(f"metadata_{key}_mismatch")
        recorded_duration = row.get("duration_seconds", "").strip()
        if recorded_duration and abs(float(recorded_duration) - result.duration_seconds) > 0.01:
            issues.append("metadata_duration_mismatch")
        if result.duration_seconds < 0.35:
            issues.append("very_short")
        elif result.duration_seconds > 15.0:
            issues.append("very_long")
        if leading > 0.5:
            issues.append("leading_silence")
        if trailing > 0.75:
            issues.append("trailing_silence")
        if result.silence_percent > 65:
            issues.append("high_silence")
        if result.clipping_percent > 0.1:
            issues.append("clipping")
        if abs(result.dc_offset) > 0.02:
            issues.append("dc_offset")
        if result.nearly_empty:
            issues.append("nearly_empty")
    except Exception as exc:  # el informe debe conservar el error por fila
        issues.append(f"unreadable:{type(exc).__name__}:{exc}")

    hard = {"missing_audio", "sha256_mismatch", "nearly_empty"}
    review = {"very_short", "very_long", "clipping", "dc_offset"}
    if not result.readable or any(issue.split(":", 1)[0] in hard for issue in issues):
        result.severity = "ERROR"
    elif any(issue in review or issue.startswith("metadata_") for issue in issues):
        result.severity = "REVIEW"
    elif issues:
        result.severity = "WARNING"
    else:
        result.severity = "INFO"
    result.issues = ";".join(issues)
    return result


def mark_duplicates(results: list[AudioMetrics]) -> None:
    for field, output_field, prefix in (
        ("pcm_sha256", "exact_duplicate_group", "exact"),
        ("acoustic_fingerprint", "acoustic_duplicate_group", "acoustic"),
    ):
        groups: dict[str, list[AudioMetrics]] = defaultdict(list)
        for result in results:
            value = getattr(result, field)
            if value:
                groups[value].append(result)
        index = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            index += 1
            group_id = f"{prefix}_{index:04d}"
            for member in members:
                setattr(member, output_field, group_id)
                issue = "exact_audio_duplicate" if prefix == "exact" else "acoustic_duplicate_candidate"
                member.issues = ";".join(filter(None, (member.issues, issue)))
                if member.severity == "INFO":
                    member.severity = "REVIEW"


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_write_bytes(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() != payload:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.stem}.preexisting_{stamp}{path.suffix}")
        shutil.copy2(path, backup)
    path.write_bytes(payload)


def select_references(rows: list[dict[str, str]], metrics: dict[str, AudioMetrics]) -> list[dict[str, object]]:
    preferred_emotions = ("neutral", "sonriente", "travieso", "sorprendido", "emocionado", "asustado", "enfadado", "curioso", "confiado", "decidido", "jugueton")
    selected: list[dict[str, object]] = []
    used: set[str] = set()
    for wanted in preferred_emotions:
        candidates = []
        for row in rows:
            metric = metrics[row["sample_id"]]
            emotion = row.get("emotion", "").lower()
            if row.get("source_game", "").lower() != "jak2" or metric.severity == "ERROR":
                continue
            if wanted not in emotion and not (wanted == "jugueton" and "travies" in emotion):
                continue
            quality_rank = {"excelente": 0, "buena": 1, "aceptable": 2, "limite": 3}.get(row.get("quality", "").lower(), 4)
            duration = float(metric.duration_seconds or 0)
            duration_penalty = abs(duration - 5.0) if 2.0 <= duration <= 10.0 else 20 + abs(duration - 5.0)
            candidates.append((quality_rank, duration_penalty, abs(float(metric.rms_dbfs or -99) + 20), row))
        if candidates:
            row = min(candidates, key=lambda item: item[:3])[3]
            if row["sample_id"] not in used:
                used.add(row["sample_id"])
                metric = metrics[row["sample_id"]]
                selected.append({
                    "sample_id": row["sample_id"], "audio_file": row["audio_file"],
                    "emotion": row.get("emotion", ""), "quality": row.get("quality", ""),
                    "duration_seconds": metric.duration_seconds,
                    "selection_reason": "Jak II; mejor calidad disponible; duración y nivel adecuados",
                })
    return selected


def summarize(rows: list[dict[str, str]], results: list[AudioMetrics]) -> dict[str, object]:
    durations = [float(result.duration_seconds) for result in results if result.readable]
    by_game: dict[str, dict[str, float | int]] = {}
    for game in sorted({row.get("source_game", "") for row in rows}):
        subset = [r for r in results if r.source_game == game and r.readable]
        by_game[game] = {"samples": len(subset), "duration_seconds": round(sum(float(r.duration_seconds) for r in subset), 3)}
    categorical = {field: dict(sorted(Counter(row.get(field, "") for row in rows).items())) for field in CATEGORICAL_FIELDS}
    return {
        "samples": len(rows),
        "readable_wavs": sum(r.readable for r in results),
        "duration_seconds": round(sum(durations), 3),
        "duration_hours": round(sum(durations) / 3600, 4),
        "duration_min_seconds_max": [round(min(durations), 4), round(statistics.median(durations), 4), round(max(durations), 4)] if durations else [],
        "severity": dict(sorted(Counter(r.severity for r in results).items())),
        "exact_duplicate_groups": len({r.exact_duplicate_group for r in results if r.exact_duplicate_group}),
        "acoustic_duplicate_candidate_groups": len({r.acoustic_duplicate_group for r in results if r.acoustic_duplicate_group}),
        "by_game": by_game,
        "categorical": categorical,
    }


def markdown_table(mapping: dict[str, object]) -> str:
    return "\n".join(["| Valor | Recuento |", "|---|---:|"] + [f"| {key or '(vacío)'} | {value} |" for key, value in mapping.items()])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, default=1300)
    parser.add_argument("--expected-metadata-sha256", default="")
    args = parser.parse_args()

    metadata = args.metadata.resolve()
    audio_root = args.audio_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata_hash = sha256_file(metadata)
    if args.expected_metadata_sha256 and metadata_hash != args.expected_metadata_sha256.lower():
        raise SystemExit(f"Hash maestro inesperado: {metadata_hash}")
    with metadata.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    missing_columns = EXPECTED_COLUMNS - set(fields)
    if missing_columns:
        raise SystemExit(f"Faltan columnas: {sorted(missing_columns)}")
    if len(rows) != args.expected_rows:
        raise SystemExit(f"Filas: {len(rows)}; esperadas: {args.expected_rows}")
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise SystemExit("sample_id duplicado")
    if len({row["audio_file"] for row in rows}) != len(rows):
        raise SystemExit("audio_file duplicado")
    if any(not row["text"].strip() or not row["normalized_text"].strip() for row in rows):
        raise SystemExit("Hay textos canónicos vacíos")
    if any(row.get("review_status", "") not in {"accepted", "accepted_with_notes"} for row in rows):
        raise SystemExit("Hay filas pendientes de aceptación")
    if any(row.get("needs_human_review", "").strip().lower() not in {"false", "0", "no"} for row in rows):
        raise SystemExit("Hay filas pendientes de revisión humana")

    immutable = output / f"metadata_daxter_final.immutable.{metadata_hash[:16]}.csv"
    if immutable.exists() and sha256_file(immutable) != metadata_hash:
        raise SystemExit(f"La copia inmutable existente no coincide: {immutable.name}")
    if not immutable.exists():
        shutil.copy2(metadata, immutable)

    results = [audit_wav(row, audio_root) for row in rows]
    mark_duplicates(results)
    dictionaries = [asdict(result) for result in results]
    write_csv(output / "AUDIO_AUDIT_FULL.csv", dictionaries, FULL_FIELDS)
    write_csv(output / "AUDIO_AUDIT_EXCEPTIONS.csv", [row for row in dictionaries if row["severity"] != "INFO"], FULL_FIELDS)

    summary = summarize(rows, results)
    stats_json = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    safe_write_bytes(output / "DATASET_STATISTICS.json", stats_json)
    stats_lines = ["# Estadísticas finales del dataset Daxter", "", f"- Muestras: {summary['samples']}", f"- Duración total: {summary['duration_hours']} h", "", "## Juegos", "", "| Juego | Muestras | Segundos |", "|---|---:|---:|"]
    stats_lines += [f"| {game} | {values['samples']} | {values['duration_seconds']} |" for game, values in summary["by_game"].items()]
    for field, values in summary["categorical"].items():
        stats_lines += ["", f"## {field}", "", markdown_table(values)]
    safe_write_bytes(output / "DATASET_STATISTICS.md", ("\n".join(stats_lines) + "\n").encode("utf-8"))

    severity = summary["severity"]
    report = f"""# Auditoría técnica final de audio — Daxter

Fecha UTC: {datetime.now(timezone.utc).isoformat()}

## Resultado

- CSV maestro: `{metadata.name}`
- SHA-256 maestro: `{metadata_hash}`
- Filas, `sample_id` y `audio_file` únicos: {len(rows)}
- WAV legibles: {summary['readable_wavs']} / {len(rows)}
- Duración total: {summary['duration_seconds']} s ({summary['duration_hours']} h)
- Severidad: {json.dumps(severity, ensure_ascii=False)}
- Grupos duplicados PCM exactos: {summary['exact_duplicate_groups']}
- Candidatos acústicos conservadores: {summary['acoustic_duplicate_candidate_groups']}

Los candidatos acústicos son avisos para escucha; no autorizan borrado automático.
Umbrales: silencio -40 dBFS; casi vacío < -50 dBFS; clipping > 0,1 %;
silencio inicial > 0,5 s; silencio final > 0,75 s.
"""
    safe_write_bytes(output / "AUDIO_AUDIT_REPORT.md", report.encode("utf-8"))

    metrics_by_id = {result.sample_id: result for result in results}
    references = select_references(rows, metrics_by_id)
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": "daxter_es_final_1300",
        "status": "ready_for_evaluation" if severity.get("ERROR", 0) == 0 else "blocked_by_errors",
        "metadata": {"file": metadata.name, "sha256": metadata_hash, "rows": len(rows), "columns": len(fields)},
        "audio": {
            "relative_root": Path(os.path.relpath(audio_root, output)).as_posix(),
            "files": len(results),
            "summary": summary,
        },
        "reference_selection": {"policy": "Jak II, calidad más alta disponible, audio limpio, duración útil y diversidad emocional", "samples": references},
        "canonical_text_policy": "text y normalized_text conservados byte por byte; esta auditoría no los reescribe",
    }
    safe_write_bytes(output / "MANIFEST_DAXTER_FINAL.json", (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    final_report = f"""# Cierre técnico del dataset final de Daxter

## Declaración verificable

El maestro contiene exactamente {len(rows)} muestras aceptadas, sin revisión humana pendiente,
con identificadores únicos y textos canónicos no modificados. Su SHA-256 es `{metadata_hash}`.
El estado técnico es **{manifest['status']}**.

## Evidencias

- Copia inmutable: `{immutable.name}`
- Manifiesto: `MANIFEST_DAXTER_FINAL.json`
- Auditoría completa y excepciones: `AUDIO_AUDIT_FULL.csv`, `AUDIO_AUDIT_EXCEPTIONS.csv`
- Estadísticas: `DATASET_STATISTICS.json`, `DATASET_STATISTICS.md`
- Hashes: `SHA256SUMS.txt`

La selección de referencias usa Jak II y la mejor calidad presente. El valor `excelente` no existe
en el maestro recibido; se emplea `buena` como nivel máximo disponible, sin alterar etiquetas humanas.
"""
    safe_write_bytes(output / "DATASET_FINAL_REPORT.md", final_report.encode("utf-8"))

    hash_targets = [metadata, immutable] + [audio_root / row.get("relative_path", row["audio_file"]) for row in rows]
    hash_targets += [output / name for name in (
        "AUDIO_AUDIT_FULL.csv", "AUDIO_AUDIT_EXCEPTIONS.csv", "AUDIO_AUDIT_REPORT.md",
        "DATASET_STATISTICS.json", "DATASET_STATISTICS.md", "DATASET_FINAL_REPORT.md",
        "MANIFEST_DAXTER_FINAL.json",
    )]
    lines = []
    for path in hash_targets:
        if path == metadata:
            label = metadata.name
        elif path.parent == audio_root:
            relative_audio_root = Path(os.path.relpath(audio_root, output)).as_posix()
            label = f"{relative_audio_root}/{path.name}"
        else:
            label = path.name
        lines.append(f"{sha256_file(path)}  {label}")
    safe_write_bytes(output / "SHA256SUMS.txt", ("\n".join(lines) + "\n").encode("utf-8"))
    print(json.dumps({"manifest_status": manifest["status"], "summary": summary, "references": references}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "ready_for_evaluation" else 2


if __name__ == "__main__":
    raise SystemExit(main())
