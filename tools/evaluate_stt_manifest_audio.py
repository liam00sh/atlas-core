"""Mide STT real sobre los WAV de un manifiesto privado."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_stt_conversation_battery import distance, words
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService
from voice.text_normalizer import ContextualTranscriptNormalizer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    config = STTConfig(model="medium", model_path=args.model_path) if args.model_path else STTConfig.from_env()
    service = STTService(
        FasterWhisperSTTProvider(config),
        AudioConverter(timeout_seconds=min(config.timeout_seconds, 30.0)),
        config=config,
        work_dir=args.output.parent / "stt_work",
    )
    results = []
    errors = 0
    word_total = 0
    exact = 0
    for item in payload["samples"]:
        source = args.manifest.parent / item["file"]
        result, timings = service.transcribe(source, language_hint="es", context_hint="general")
        normalized = ContextualTranscriptNormalizer.normalize(result)
        expected_words = words(item["text"])
        observed_words = words(normalized.text)
        current_errors = distance(expected_words, observed_words)
        word_total += len(expected_words)
        errors += current_errors
        exact += expected_words == observed_words
        results.append({
            "index": item["index"],
            "file": item["file"],
            "expected": item["text"],
            "raw_transcript": result.text,
            "normalized_transcript": normalized.text,
            "confidence": result.confidence.value,
            "word_errors": current_errors,
            "reference_words": len(expected_words),
            "stt_ms": timings.get("stt.transcribe"),
        })
    report = {
        "schema_version": 1,
        "source_kind": "synthetic_b1_audio_not_human_speech",
        "measured_cases": len(results),
        "exact_match": round(exact / len(results), 4),
        "wer": round(errors / word_total, 4) if word_total else None,
        "results": results,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
