"""Convierte la batería base con OpenVoice V2 y la referencia de Daxter."""

from __future__ import annotations

import argparse
import platform
from pathlib import Path

import psutil
import torch
from TTS.api import TTS

from tools.voice_lab_battery import BATTERY, Timer, wav_duration, write_results


MODEL = "voice_conversion_models/multilingual/multi-dataset/openvoice_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    process = psutil.Process()
    ram_before = process.memory_info().rss / 1024**2
    if device == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    with Timer() as init_timer:
        converter = TTS(model_name=MODEL, progress_bar=False).to(device)
    runs = []
    for case_id, prompt in BATTERY[: args.limit or None]:
        source = args.source_dir / f"{case_id}.wav"
        output = args.output_dir / f"{case_id}.wav"
        error = ""
        seconds = 0.0
        try:
            if not source.is_file():
                raise FileNotFoundError(source)
            if device == "cuda":
                torch.cuda.reset_peak_memory_stats()
            with Timer() as timer:
                converter.voice_conversion_to_file(
                    source_wav=str(source), target_wav=str(args.reference), file_path=str(output)
                )
            seconds = timer.seconds
            duration = wav_duration(output)
        except Exception as exc:
            duration = 0.0
            error = f"{type(exc).__name__}: {exc}"
        peak_vram = torch.cuda.max_memory_allocated() / 1024**2 if device == "cuda" else 0.0
        runs.append({
            "case_id": case_id, "text": prompt, "output_file": output.name,
            "generation_seconds": round(seconds, 4), "audio_seconds": round(duration, 4),
            "rtf": round(seconds / duration, 4) if duration else "", "peak_vram_mb": round(peak_vram, 1), "error": error,
        })
    sample_rate = "per_source"
    if runs and (args.output_dir / runs[0]["output_file"]).is_file():
        import wave
        with wave.open(str(args.output_dir / runs[0]["output_file"]), "rb") as handle:
            sample_rate = handle.getframerate()
    write_results(args.output_dir, "openvoice_v2_coqui_tts_0.27.5", runs, {
        "mode": "tts_plus_voice_conversion", "base_engine": "chatterbox_multilingual_0.1.7",
        "model": MODEL, "device": device, "initialization_seconds": round(init_timer.seconds, 4),
        "ram_before_mb": round(ram_before, 1), "ram_after_mb": round(process.memory_info().rss / 1024**2, 1),
        "python": platform.python_version(), "torch": torch.__version__, "sample_rate": sample_rate,
        "reference_file": args.reference.name,
    })
    return 1 if any(row["error"] for row in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
