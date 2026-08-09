"""Ejecuta Chatterbox Multilingual localmente con la batería común."""

from __future__ import annotations

import argparse
import platform
from pathlib import Path

import psutil
import torch
import torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

from tools.voice_lab_battery import BATTERY, Timer, wav_duration, write_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    process = psutil.Process()
    ram_before = process.memory_info().rss / 1024**2
    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    with Timer() as init_timer:
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    runs = []
    cases = BATTERY[: args.limit or None]
    for case_id, prompt in cases:
        output = args.output_dir / f"{case_id}.wav"
        error = ""
        seconds = 0.0
        try:
            if device.type == "cuda":
                torch.cuda.reset_peak_memory_stats()
            with Timer() as timer:
                audio = model.generate(
                    prompt,
                    language_id="es",
                    audio_prompt_path=str(args.reference),
                    exaggeration=0.65 if case_id not in {"01_neutral", "12_numeros_nombres", "13_larga"} else 0.45,
                    cfg_weight=0.35,
                )
                torchaudio.save(
                    str(output), audio.cpu(), model.sr,
                    encoding="PCM_S", bits_per_sample=16,
                )
            seconds = timer.seconds
            duration = wav_duration(output)
        except Exception as exc:
            duration = 0.0
            error = f"{type(exc).__name__}: {exc}"
        peak_vram = torch.cuda.max_memory_allocated() / 1024**2 if device.type == "cuda" else 0.0
        runs.append({
            "case_id": case_id, "text": prompt, "output_file": output.name,
            "generation_seconds": round(seconds, 4), "audio_seconds": round(duration, 4),
            "rtf": round(seconds / duration, 4) if duration else "", "peak_vram_mb": round(peak_vram, 1), "error": error,
        })
    write_results(args.output_dir, "chatterbox_multilingual_0.1.7", runs, {
        "mode": "zero_shot_voice_cloning", "language": "es", "device": str(device),
        "initialization_seconds": round(init_timer.seconds, 4),
        "ram_before_mb": round(ram_before, 1), "ram_after_mb": round(process.memory_info().rss / 1024**2, 1),
        "python": platform.python_version(), "torch": torch.__version__, "sample_rate": model.sr,
        "reference_file": args.reference.name,
    })
    return 1 if any(row["error"] for row in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
