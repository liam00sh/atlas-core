"""Crea referencias trazables de conditioning para la Ronda B."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import torch
import torchaudio


DIVERSE_IDS = ("daxter_0465_jak2_ds305", "daxter_0288_jak2_ds047", "daxter_0344_jak2_ds166")
SPAIN_NAMES_IDS = (
    "daxter_0339_jak2_ds161",  # Jak, vamos a echarle un vistazo.
    "daxter_0616_jak3_dax146",  # Espera aquí. Ahora vuelvo.
    "daxter_0969_jak3_dax624",  # Hola compi, en marcha.
    "daxter_0338_jak2_ds160",  # piedra Precursor
    "daxter_0462_jak2_ds289",  # eco oscuro
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_mono(path: Path, rate: int) -> torch.Tensor:
    waveform, source_rate = torchaudio.load(str(path))
    waveform = waveform.mean(dim=0, keepdim=True)
    if source_rate != rate:
        waveform = torchaudio.functional.resample(waveform, source_rate, rate)
    return waveform


def concatenate(paths: list[Path], target: Path, rate: int = 48000) -> float:
    silence = torch.zeros(1, int(rate * 0.08))
    pieces = []
    for index, path in enumerate(paths):
        if index:
            pieces.append(silence)
        pieces.append(load_mono(path, rate))
    waveform = torch.cat(pieces, dim=1)
    torchaudio.save(str(target), waveform, rate, encoding="PCM_S", bits_per_sample=16)
    return round(waveform.shape[1] / rate, 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if sha256_file(args.metadata) != args.expected_metadata_sha256.casefold():
        raise SystemExit("El hash del metadata maestro ha cambiado")
    with args.metadata.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["sample_id"]: row for row in csv.DictReader(handle)}
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    reference_rows = manifest["reference_selection"]["samples"]
    emotion_ids = {row["emotion"]: row["sample_id"] for row in reference_rows}
    emotion_ids.setdefault("determinado", emotion_ids.get("confiado"))
    emotion_ids.setdefault("jugueton", emotion_ids.get("travieso"))
    trace = []

    def source(sample_id: str) -> Path:
        row = rows[sample_id]
        path = args.audio_root / (row.get("relative_path") or row["audio_file"])
        if not path.is_file() or sha256_file(path) != row["sha256"].casefold():
            raise SystemExit(f"Referencia ausente o alterada: {sample_id}")
        return path

    for emotion, sample_id in sorted(emotion_ids.items()):
        if not sample_id:
            continue
        target = output / f"emotion_{emotion}.wav"
        duration = concatenate([source(sample_id)], target)
        row = rows[sample_id]
        trace.append({"strategy": "emotion_matched", "emotion": emotion, "sample_id": sample_id, "audio_file": row["audio_file"], "text": row["text"], "output_file": target.name, "duration_seconds": duration})
    combined = {}
    for strategy, sample_ids, filename in (
        ("jak2_diverse", DIVERSE_IDS, "reference_daxter_jak2_diverse.wav"),
        ("spain_names", SPAIN_NAMES_IDS, "reference_daxter_spain_names.wav"),
    ):
        target = output / filename
        duration = concatenate([source(sample_id) for sample_id in sample_ids], target)
        combined[strategy] = {"file": target.name, "duration_seconds": duration, "sample_ids": list(sample_ids)}
        for sample_id in sample_ids:
            row = rows[sample_id]
            trace.append({"strategy": strategy, "emotion": row["emotion"], "sample_id": sample_id, "audio_file": row["audio_file"], "text": row["text"], "output_file": target.name, "duration_seconds": row["duration_seconds"]})
    config = {
        "sample_rate": 48000,
        "combined": combined,
        "emotions": {emotion: f"emotion_{emotion}.wav" for emotion in emotion_ids if emotion_ids[emotion]},
        "fallback_emotion": "neutral",
        "note": "Las referencias se derivan de WAV originales verificados; no hay ajuste de pesos.",
    }
    (output / "REFERENCE_CONFIG.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ("strategy", "emotion", "sample_id", "audio_file", "text", "output_file", "duration_seconds")
    with (output / "REFERENCE_TRACE.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trace)
    targets = sorted(output.glob("*.wav")) + [output / "REFERENCE_CONFIG.json", output / "REFERENCE_TRACE.csv"]
    (output / "SHA256SUMS.txt").write_text("".join(f"{sha256_file(path)}  {path.name}\n" for path in targets), encoding="utf-8")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
