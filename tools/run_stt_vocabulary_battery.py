"""Run a transparent raw-versus-normalized STT vocabulary battery."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService
from voice.text_normalizer import ContextualTranscriptNormalizer


TERMS = (
    "Daxter", "Atlas", "Telegram", "cancelar", "confirmar",
    "enciende", "apaga", "acuario peque\u00f1o", "Docker",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--without-context", action="store_true")
    parser.add_argument("--hotwords-only", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    config = STTConfig(model_path=args.model_path) if args.model_path else STTConfig.from_env()
    if args.without_context:
        config = STTConfig(
            model=config.model,
            model_path=config.model_path,
            device=config.device,
            compute_type=config.compute_type,
            timeout_seconds=config.timeout_seconds,
            max_audio_seconds=config.max_audio_seconds,
            allow_model_download=config.allow_model_download,
            language_hint=config.language_hint,
            beam_size=5,
            initial_prompt="",
            hotwords="",
        )
    elif args.hotwords_only:
        config = STTConfig(
            model=config.model,
            model_path=config.model_path,
            device=config.device,
            compute_type=config.compute_type,
            timeout_seconds=config.timeout_seconds,
            max_audio_seconds=config.max_audio_seconds,
            allow_model_download=config.allow_model_download,
            language_hint=config.language_hint,
            beam_size=config.beam_size,
            initial_prompt="",
            hotwords=config.hotwords,
        )
    service = STTService(
        FasterWhisperSTTProvider(config),
        AudioConverter(timeout_seconds=min(30.0, config.timeout_seconds)),
        config=config,
        work_dir=args.output.parent / "work",
    )
    rows = []
    for index, expected in enumerate(TERMS, 1):
        source = args.input_dir / f"{index:02d}.wav"
        if not source.is_file():
            rows.append({"id": index, "expected": expected, "file": str(source), "status": "missing"})
            continue
        raw, timings = service.transcribe(source, language_hint="es")
        normalized = ContextualTranscriptNormalizer.normalize(raw)
        rows.append({
            "id": index,
            "expected": expected,
            "file": str(source),
            "status": "ok",
            "raw_transcript": raw.text,
            "normalized_transcript": normalized.text,
            "confidence": raw.confidence.value,
            "confidence_score": raw.confidence_score,
            "mean_word_probability": raw.mean_word_probability,
            "stt_ms": timings.get("stt.transcribe"),
        })
    fields = (
        "id", "expected", "file", "status", "raw_transcript",
        "normalized_transcript", "confidence", "confidence_score",
        "mean_word_probability", "stt_ms",
    )
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return 0 if all(row["status"] == "ok" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
