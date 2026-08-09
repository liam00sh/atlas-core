"""Calcula similitud ECAPA para cada candidato y batería de Ronda B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn.functional as functional
import torchaudio
from speechbrain.inference.classifiers import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy


def embedding(model: EncoderClassifier, path: Path) -> torch.Tensor:
    waveform, rate = torchaudio.load(str(path))
    waveform = waveform.mean(dim=0, keepdim=True)
    if rate != 16000:
        waveform = torchaudio.functional.resample(waveform, rate, 16000)
    with torch.inference_mode():
        value = model.encode_batch(waveform).squeeze()
    return functional.normalize(value, dim=0).cpu()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", type=Path, nargs="+", required=True)
    parser.add_argument("--lab-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--model-source", type=Path)
    args = parser.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = EncoderClassifier.from_hparams(
        source=str(args.model_source) if args.model_source else "speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(args.model_cache),
        run_opts={"device": device}, local_strategy=LocalStrategy.COPY,
    )
    ref_vectors = [embedding(model, path) for path in args.references]
    reference = functional.normalize(torch.stack(ref_vectors).mean(dim=0), dim=0)
    result = {
        "model": "speechbrain/spkrec-ecapa-voxceleb", "device": device,
        "interpretation": "Métrica aproximada de hablante; no evalúa acento, pronunciación, emoción ni naturalidad.",
        "references": [path.name for path in args.references], "candidates": {},
    }
    for candidate_dir in sorted(args.lab_dir.glob("candidate_B*")):
        candidate = candidate_dir.name.removeprefix("candidate_")
        result["candidates"][candidate] = {}
        for battery_dir in sorted(candidate_dir.glob("benchmark_*")):
            battery = battery_dir.name.removeprefix("benchmark_")
            rows = []
            for path in sorted(battery_dir.glob("*.wav")):
                score = functional.cosine_similarity(reference, embedding(model, path), dim=0).item()
                rows.append({"case_id": path.stem, "file": path.name, "cosine_similarity": round(score, 5)})
            scores = [row["cosine_similarity"] for row in rows]
            result["candidates"][candidate][battery] = {
                "mean": round(sum(scores) / len(scores), 5), "min": min(scores), "max": max(scores), "files": rows,
            }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
