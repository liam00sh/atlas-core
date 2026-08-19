"""Worker local para una sola variante de la comparativa TTS privada."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys
from time import perf_counter
import wave


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.chatterbox_worker import _trim_and_fade
from tools.chatterbox_es_es_runtime import cap_generation, load_es_es_model
from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter


def _seed_everything(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _load(args):
    import torch

    source = args.source.resolve()
    source_path = source / ("chatterbox/src" if args.candidate == "es_es" else "src")
    sys.path.insert(0, str(source_path))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.candidate == "es_es":
        model, _route = load_es_es_model(source=source, model_dir=args.model_dir, device=device)
        return model, device
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    version = "v2" if args.candidate == "v2" else "v3"
    model = ChatterboxMultilingualTTS.from_local(args.model_dir, device, t3_model=version)
    cap_generation(model)
    return model, device


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=("v2", "v3", "es_es"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.source, args.model_dir, args.reference):
        if not path.exists():
            parser.error(f"No existe: {path}")

    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "NO_PROXY": "*"})
    requests = json.load(sys.stdin)
    model, device = _load(args)
    import torch
    import torchaudio

    results = []
    for item in requests:
        target = Path(item["output"])
        target.parent.mkdir(parents=True, exist_ok=True)
        normalized = ChatterboxStyleAdapter.normalize_text(item["text"])
        # Los decodificadores oficiales pueden entrar en continuaciones muy
        # costosas con frases largas. El techo común mantiene la comparación
        # terminable en una GPU de 8 GiB y expone cualquier posible corte.
        token_limit = min(110, max(90, round(len(normalized) * 1.5)))
        if target.is_file() and target.stat().st_size > 44:
            try:
                with wave.open(str(target), "rb") as wav:
                    duration = wav.getnframes() / wav.getframerate()
                if 0 < duration < 60.0:
                    results.append({
                        "blind_id": item["blind_id"], "success": True, "reused": True,
                        "audio_seconds": round(duration, 4), "max_new_tokens": token_limit,
                        "possible_truncation": duration >= (token_limit / 25.0) * 0.94,
                    })
                    continue
            except (OSError, EOFError, wave.Error):
                pass
        _seed_everything(int(item["seed"]))
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        started = perf_counter()
        kwargs = dict(
            audio_prompt_path=str(args.reference), exaggeration=0.45,
            cfg_weight=0.35, temperature=0.8, language_id="es",
        )
        if args.candidate != "es_es":
            kwargs.update(repetition_penalty=2.0, min_p=0.05, top_p=1.0)
        try:
            model._atlas_max_new_tokens = token_limit
            print(f"START {item['blind_id']} max_new_tokens={token_limit}", file=sys.stderr, flush=True)
            audio = model.generate(normalized, **kwargs)
            print(f"TOKENS_DONE {item['blind_id']}", file=sys.stderr, flush=True)
            audio = _trim_and_fade(audio, model.sr, {
                "trim_start": False, "trim_end": True, "threshold": 0.0005,
                "end_padding_ms": 80, "ensure_end_padding": True, "fade_ms": 5,
            })
            torchaudio.save(str(target), audio.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
            if device.type == "cuda":
                torch.cuda.synchronize()
            elapsed = perf_counter() - started
            with wave.open(str(target), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            results.append({
                "blind_id": item["blind_id"], "success": True,
                "generation_seconds": round(elapsed, 4), "audio_seconds": round(duration, 4),
                "rtf": round(elapsed / duration, 4) if duration else None,
                "peak_vram_bytes": int(torch.cuda.max_memory_allocated()) if device.type == "cuda" else 0,
                "normalized_text": normalized, "max_new_tokens": token_limit,
                "possible_truncation": duration >= (token_limit / 25.0) * 0.94,
            })
            print(f"DONE {item['blind_id']} seconds={duration:.4f}", file=sys.stderr, flush=True)
        except Exception as exc:
            target.unlink(missing_ok=True)
            results.append({"blind_id": item["blind_id"], "success": False, "error": f"{type(exc).__name__}: {exc}"})
    payload = {"candidate": args.candidate, "device": str(device), "results": results}
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(args.result)
    return 0 if all(row["success"] for row in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
