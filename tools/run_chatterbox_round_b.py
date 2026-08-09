"""Genera candidatos B0-B3 de Chatterbox con conditioning reproducible.

B0/original copia byte por byte la salida ganadora de Ronda A. El resto usa
seed fija, registra el texto solicitado y el texto de inferencia por separado,
y deja un progreso JSONL que permite reanudar sin regenerar WAV válidos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import inspect
import json
import platform
import random
import shutil
import time
import wave
from array import array
from pathlib import Path

from tools.round_b_battery import CANDIDATES, battery, exaggeration, normalize_for_inference


FIELDS = (
    "candidate", "battery", "case_id", "emotion", "requested_text", "synthesis_text",
    "output_file", "reference_file", "seed", "generation_seconds", "audio_seconds", "rtf",
    "peak_vram_mb", "sample_rate", "channels", "bits", "leading_silence_seconds",
    "trailing_silence_seconds", "automatic_flags", "inherited_round_a", "error",
)


def stable_seed(base: int, *parts: str) -> int:
    digest = hashlib.sha256((str(base) + "|" + "|".join(parts)).encode()).digest()
    return base + int.from_bytes(digest[:4], "big") % 1_000_000


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def wav_metrics(path: Path, requested_text: str) -> dict[str, object]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    values = array("h")
    if width == 2:
        values.frombytes(raw)
    threshold = 32767 * (10 ** (-40 / 20))
    mono = list(values[::channels]) if values else []
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
    duration = frames / rate
    expected = max(0.8, len(requested_text.split()) / 2.6)
    flags = []
    if duration > expected * 2.4 and duration - expected > 4:
        flags.append("duration_excess_possible_repetition_or_hallucination")
    if duration < expected * 0.45:
        flags.append("duration_short_possible_truncation")
    if leading / rate > 0.4:
        flags.append("leading_silence")
    if trailing / rate > 0.6:
        flags.append("trailing_silence")
    return {
        "audio_seconds": round(duration, 4), "sample_rate": rate, "channels": channels,
        "bits": width * 8, "leading_silence_seconds": round(leading / rate, 4),
        "trailing_silence_seconds": round(trailing / rate, 4), "automatic_flags": ";".join(flags),
    }


def write_benchmark(folder: Path, candidate: str, battery_name: str, rows: list[dict], metadata: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    payload = {"candidate": candidate, "battery": battery_name, "metadata": metadata, "runs": rows}
    (folder / "benchmark.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (folder / "benchmark.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def inherit_round_a(round_a: Path, destination: Path) -> list[dict]:
    data = json.loads((round_a / "benchmark.json").read_text(encoding="utf-8"))
    rows = []
    for source_row in data["runs"]:
        source = round_a / source_row["output_file"]
        target = destination / source.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        metrics = wav_metrics(target, source_row["text"])
        rows.append({
            "candidate": "B0", "battery": "original", "case_id": source_row["case_id"],
            "emotion": "", "requested_text": source_row["text"], "synthesis_text": source_row["text"],
            "output_file": target.name, "reference_file": data["metadata"]["reference_file"], "seed": "",
            "generation_seconds": source_row["generation_seconds"], "rtf": source_row["rtf"],
            "peak_vram_mb": source_row["peak_vram_mb"], "inherited_round_a": True,
            "error": source_row["error"], **metrics,
        })
    write_benchmark(destination, "B0", "original", rows, {
        **data["metadata"], "source": "Ronda A; WAV copiados byte por byte", "reproducible_seed": False,
    })
    return rows


def reference_for(config: dict, references: Path, reference_config: dict, emotion: str) -> Path:
    strategy = config["reference_strategy"]
    if strategy == "emotion_matched":
        filename = reference_config["emotions"].get(emotion)
        if not filename:
            filename = reference_config["emotions"][reference_config["fallback_emotion"]]
    else:
        filename = reference_config["combined"][strategy]["file"]
    return references / filename


def load_progress(path: Path) -> dict[str, dict]:
    result = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                result[row["case_id"]] = row
    return result


def main() -> int:
    import psutil
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-dir", type=Path, required=True)
    parser.add_argument("--reference-config", type=Path, required=True)
    parser.add_argument("--round-a-engine-dir", type=Path, required=True)
    parser.add_argument("--candidate", action="append", choices=tuple(CANDIDATES))
    parser.add_argument("--battery", choices=("original", "corrected", "both"), default="both")
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--official-commit", default="5de7a54aa4e5e2baadb0182dde554908b48b85c2")
    args = parser.parse_args()
    lab = args.lab_dir.resolve()
    references = args.reference_config.resolve().parent
    reference_config = json.loads(args.reference_config.read_text(encoding="utf-8"))
    selected = args.candidate or list(CANDIDATES)
    batteries = ("original", "corrected") if args.battery == "both" else (args.battery,)
    lab.mkdir(parents=True, exist_ok=True)

    if "B0" in selected and "original" in batteries:
        inherit_round_a(args.round_a_engine_dir.resolve(), lab / "candidate_B0" / "benchmark_original")
    generation_jobs = [(candidate, name) for candidate in selected for name in batteries if not (candidate == "B0" and name == "original")]
    if not generation_jobs:
        return 0

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    process = psutil.Process()
    ram_before = process.memory_info().rss / 1024**2
    if device.type == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    init_start = time.perf_counter()
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    init_seconds = time.perf_counter() - init_start
    all_errors = []

    for candidate, battery_name in generation_jobs:
        config = CANDIDATES[candidate]
        folder = lab / f"candidate_{candidate}" / f"benchmark_{battery_name}"
        folder.mkdir(parents=True, exist_ok=True)
        progress_path = folder / "progress.jsonl"
        prior = load_progress(progress_path) if args.resume else {}
        rows = []
        cases = battery(battery_name)[: args.limit or None]
        for case_id, requested_text, emotion in cases:
            if case_id in prior and (folder / prior[case_id]["output_file"]).is_file() and not prior[case_id].get("error"):
                rows.append(prior[case_id])
                continue
            output = folder / f"{case_id}.wav"
            reference = reference_for(config, references, reference_config, emotion)
            synthesis_text = normalize_for_inference(requested_text) if config["normalize_pronunciation"] else requested_text
            seed = stable_seed(args.seed, candidate, battery_name, case_id)
            set_seed(seed)
            if device.type == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            error = ""
            try:
                audio = model.generate(
                    synthesis_text,
                    language_id="es",
                    audio_prompt_path=str(reference),
                    exaggeration=exaggeration(case_id, emotion, candidate),
                    cfg_weight=config["cfg_weight"],
                    temperature=config["temperature"],
                    repetition_penalty=config["repetition_penalty"],
                    min_p=config["min_p"],
                    top_p=config["top_p"],
                )
                torchaudio.save(str(output), audio.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
                metrics = wav_metrics(output, requested_text)
            except Exception as exc:
                metrics = {"audio_seconds": 0, "sample_rate": "", "channels": "", "bits": "", "leading_silence_seconds": "", "trailing_silence_seconds": "", "automatic_flags": ""}
                error = f"{type(exc).__name__}: {exc}"
                all_errors.append((candidate, battery_name, case_id, error))
            seconds = time.perf_counter() - started
            peak = torch.cuda.max_memory_allocated() / 1024**2 if device.type == "cuda" else 0.0
            row = {
                "candidate": candidate, "battery": battery_name, "case_id": case_id, "emotion": emotion,
                "requested_text": requested_text, "synthesis_text": synthesis_text, "output_file": output.name,
                "reference_file": reference.name, "seed": seed, "generation_seconds": round(seconds, 4),
                "rtf": round(seconds / metrics["audio_seconds"], 4) if metrics["audio_seconds"] else "",
                "peak_vram_mb": round(peak, 1), "inherited_round_a": False, "error": error, **metrics,
            }
            rows.append(row)
            with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        write_benchmark(folder, candidate, battery_name, rows, {
            "engine": "chatterbox_multilingual_0.1.7", "mode": "zero_shot_conditioning_round_b",
            "device": str(device), "language_id": "es", "reference_strategy": config["reference_strategy"],
            "normalization": config["normalize_pronunciation"], "parameters": {key: config[key] for key in ("cfg_weight", "temperature", "repetition_penalty", "min_p", "top_p")},
            "base_seed": args.seed, "initialization_seconds": round(init_seconds, 4), "sample_rate": model.sr,
            "purpose": config["purpose"],
        })
        (lab / f"candidate_{candidate}" / "CANDIDATE_CONFIG.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "engine": "Chatterbox Multilingual V2", "package_version": importlib.metadata.version("chatterbox-tts"),
        "official_commit_inspected": args.official_commit, "official_training_pipeline_available": False,
        "adaptation_mode": "conditioning_and_inference_normalization", "language_id": "es", "locale_parameter": False,
        "generate_signature": str(inspect.signature(model.generate)), "device": str(device),
        "python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "initialization_seconds": round(init_seconds, 4), "ram_before_mb": round(ram_before, 1),
        "ram_after_mb": round(process.memory_info().rss / 1024**2, 1), "errors": all_errors,
    }
    (lab / "ROUND_B_RUN_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
