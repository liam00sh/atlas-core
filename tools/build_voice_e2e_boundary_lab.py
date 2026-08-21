"""Genera el mini-laboratorio privado para validar límites TTS, sin tocar la E2E."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import shutil
import struct
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.models import SynthesisRequest
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.segmentation import split_for_speech


CASES = (1, 2, 8, 9, 11, 12, 13)
BOUNDARIES = {
    "A_current_80_0_fixed110": (80, 0, "fixed"),
    "B_end_120": (120, 0, "fixed"),
    "B_end_160": (160, 0, "fixed"),
    "B_end_200": (200, 0, "fixed"),
    "B_end_250": (250, 0, "fixed"),
    "C_preroll_20": (80, 20, "fixed"),
    "C_preroll_40": (80, 40, "fixed"),
    "C_preroll_60": (80, 60, "fixed"),
    "D_segmented": (200, 40, "segmented"),
    "E_candidate": (200, 40, "dynamic"),
}


def read_wav(path: Path) -> tuple[wave._wave_params, bytes]:
    with wave.open(str(path), "rb") as source:
        return source.getparams(), source.readframes(source.getnframes())


def write_wav(path: Path, params: wave._wave_params, frames: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as target:
        target.setparams(params)
        target.writeframes(frames)


def boundary_copy(source: Path, target: Path, *, end_ms: int, pre_ms: int, fade_ms: int = 5) -> None:
    params, frames = read_wav(source)
    if params.sampwidth != 2:
        raise ValueError("El laboratorio requiere WAV PCM16.")
    frame_size = params.nchannels * params.sampwidth
    pre_count = round(params.framerate * pre_ms / 1000)
    end_count = round(params.framerate * end_ms / 1000)
    samples = list(struct.unpack("<" + "h" * (len(frames) // 2), frames))
    samples = [0] * (pre_count * params.nchannels) + samples + [0] * (end_count * params.nchannels)
    fade_count = min(round(params.framerate * fade_ms / 1000), len(samples) // params.nchannels // 2)
    for frame in range(fade_count):
        gain = frame / max(1, fade_count - 1)
        for channel in range(params.nchannels):
            pos = frame * params.nchannels + channel
            samples[pos] = round(samples[pos] * gain)
    encoded = struct.pack("<" + "h" * len(samples), *samples)
    write_wav(target, params, encoded)


def concatenate(sources: list[Path], target: Path, gap_ms: int = 60) -> None:
    first_params, _ = read_wav(sources[0])
    parts = []
    gap = b"\0" * round(first_params.framerate * gap_ms / 1000) * first_params.nchannels * first_params.sampwidth
    for index, source in enumerate(sources):
        params, frames = read_wav(source)
        if (
            params.nchannels, params.sampwidth, params.framerate, params.comptype
        ) != (
            first_params.nchannels, first_params.sampwidth,
            first_params.framerate, first_params.comptype,
        ):
            raise ValueError("Los segmentos no comparten formato WAV.")
        if index:
            parts.append(gap)
        parts.append(frames)
    write_wav(target, first_params, b"".join(parts))


def synthesize(provider, text: str, target: Path):
    request = SynthesisRequest(text, "daxter_official", "daxter_es_jak2", target)
    result = provider.synthesize(request)
    if not result.success:
        raise RuntimeError(result.error or "Fallo TTS")
    return result


def metrics(path: Path) -> dict[str, object]:
    params, frames = read_wav(path)
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "samples": len(frames) // (params.nchannels * params.sampwidth),
        "duration_ms": round(len(frames) / (params.nchannels * params.sampwidth) * 1000 / params.framerate, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e2e-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tts-python", type=Path, required=True)
    parser.add_argument("--tts-source", type=Path, required=True)
    parser.add_argument("--tts-model-dir", type=Path, required=True)
    parser.add_argument("--tts-reference", type=Path, required=True)
    args = parser.parse_args()
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.e2e_results.read_text(encoding="utf-8"))
    cases = {int(row["index"]): row for row in data["cases"] if int(row["index"]) in CASES}
    common = dict(
        reference_path=args.tts_reference, candidate="es_es", source_path=args.tts_source,
        model_dir=args.tts_model_dir, worker_command=[str(args.tts_python), str(Path(__file__).with_name("chatterbox_worker.py"))],
        cache_enabled=False, postprocess=False, timeout_seconds=300,
    )
    fixed = ChatterboxDaxterProvider(**common, generation_policy={"fixed_max_new_tokens": 110})
    dynamic = ChatterboxDaxterProvider(**common)
    manifest = []
    try:
        for index in CASES:
            text = str(cases[index]["spoken_text"])
            case_dir = root / f"case_{index:03d}"
            raw_fixed = case_dir / "raw_fixed110.wav"
            raw_dynamic = case_dir / "raw_dynamic.wav"
            fixed_result = synthesize(fixed, text, raw_fixed)
            dynamic_result = synthesize(dynamic, text, raw_dynamic)
            segmented_raw = case_dir / "raw_segmented.wav"
            segment_paths = []
            segment_results = []
            for part_index, segment in enumerate(split_for_speech(text, max_chars=80), 1):
                segment_path = case_dir / f"segment_{part_index:02d}.wav"
                segment_results.append(synthesize(dynamic, segment, segment_path))
                segment_paths.append(segment_path)
            concatenate(segment_paths, segmented_raw)
            sources = {"fixed": raw_fixed, "dynamic": raw_dynamic, "segmented": segmented_raw}
            for variant, (end_ms, pre_ms, source_kind) in BOUNDARIES.items():
                output = case_dir / f"{variant}.wav"
                boundary_copy(sources[source_kind], output, end_ms=end_ms, pre_ms=pre_ms)
                generation = fixed_result if source_kind == "fixed" else dynamic_result
                row = {
                    "case": index, "text": text, "variant": variant,
                    "end_padding_ms": end_ms, "pre_roll_ms": pre_ms,
                    "segmentation": source_kind == "segmented", "path": str(output),
                    "generation_tokens_budgeted": sum(item.generation_tokens_budgeted for item in segment_results) if source_kind == "segmented" else generation.generation_tokens_budgeted,
                    "generation_tokens_used": sum(item.generation_tokens_used for item in segment_results) if source_kind == "segmented" else generation.generation_tokens_used,
                    "reached_generation_limit": any(item.reached_generation_limit for item in segment_results) if source_kind == "segmented" else generation.reached_generation_limit,
                    **metrics(output),
                }
                manifest.append(row)
    finally:
        fixed.close()
        dynamic.close()

    rng = random.Random(20260821)
    shuffled = manifest[:]
    rng.shuffle(shuffled)
    key = []
    rows = []
    cards = []
    for ordinal, row in enumerate(shuffled, 1):
        blind_id = f"M{ordinal:03d}"
        relative = Path(row["path"]).relative_to(root).as_posix()
        key.append({"blind_id": blind_id, **row})
        rows.append({"blind_id": blind_id, "case": row["case"], "complete_start_1_5": "", "complete_end_1_5": "", "naturalness_1_5": "", "artifacts_1_5": "", "accept": "", "notes": ""})
        cards.append(f'<section><h2>{blind_id} · caso {row["case"]}</h2><audio controls preload="none" src="{html.escape(relative)}"></audio></section>')
    (root / "LAB_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "BLIND_KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    with (root / "HUMAN_TTS_BOUNDARY_REVIEW.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader(); writer.writerows(rows)
    player = "<!doctype html><meta charset=utf-8><title>Atlas · prueba ciega TTS</title><style>body{font:16px system-ui;max-width:900px;margin:auto;padding:24px}section{border:1px solid #ccc;border-radius:12px;padding:14px;margin:12px}audio{width:100%}</style><h1>Mini validación ciega de límites TTS</h1><p>Valora inicio, final, naturalidad y artefactos sin abrir BLIND_KEY.json.</p>" + "".join(cards)
    (root / "BLIND_PLAYER.html").write_text(player, encoding="utf-8")
    print(json.dumps({"cases": len(CASES), "variants": len(BOUNDARIES), "clips": len(manifest), "player": str(root / "BLIND_PLAYER.html")}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
