"""Calcula similitud aproximada de hablante con ECAPA-TDNN, sin evaluar calidad humana."""

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
    parser.add_argument("--engine-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    args = parser.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(args.model_cache),
        run_opts={"device": device},
        local_strategy=LocalStrategy.COPY,
    )
    reference_vectors = [embedding(model, path) for path in args.references]
    reference = functional.normalize(torch.stack(reference_vectors).mean(dim=0), dim=0)
    result = {
        "model": "speechbrain/spkrec-ecapa-voxceleb",
        "interpretation": "cosine similarity is an approximate speaker metric, not a human quality score",
        "references": [path.name for path in args.references],
        "engines": {},
    }
    for engine_dir in args.engine_dir:
        rows = []
        for path in sorted(engine_dir.glob("*.wav")):
            score = functional.cosine_similarity(reference, embedding(model, path), dim=0).item()
            rows.append({"file": path.name, "cosine_similarity": round(score, 5)})
        scores = [row["cosine_similarity"] for row in rows]
        result["engines"][engine_dir.name] = {
            "mean": round(sum(scores) / len(scores), 5) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
            "files": rows,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
