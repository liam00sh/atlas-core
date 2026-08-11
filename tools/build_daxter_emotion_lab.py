"""Genera el laboratorio ciego de emociones sin integrar Chatterbox en Atlas Core."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import random
import shutil
import time
import wave
from array import array
from pathlib import Path

from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter
from voice.style import VoiceStyleSelector


EMOTION_TEXTS = {
    "neutral": "Todo está preparado; podemos continuar.",
    "sonriente": "Hola, REDACTED_2c7b6821719d. Me alegra verte por aquí.",
    "picaro": "Tengo una idea; técnicamente no rompe ninguna regla.",
    "sorprendido": "¡Vaya! Eso sí que no me lo esperaba.",
    "pensativo": "Espera un momento; creo que hay otra forma de hacerlo.",
    "emocionado": "¡Lo conseguimos! ¡Esto merece una celebración!",
    "asustado": "Espera, espera. ¿Has oído ese ruido detrás de nosotros?",
    "enfadado": "¡Eh! Eso no estaba permitido; devuélvelo ahora mismo.",
    "curioso": "Oye, ¿cómo funciona exactamente ese mecanismo?",
    "confiado": "Tranquilo. Lo tengo todo bajo control.",
    "risa": "Je, je. Eso ha salido mejor de lo esperado.",
    "cansado": "Ha sido una misión larga; necesito bajar un poco el ritmo.",
    "sonoliento": "Podemos continuar mañana; ahora necesito descansar.",
    "determinado": "No nos rendiremos. Encontraremos una salida.",
    "travieso": "Seguro que este botón no hace nada peligroso.",
}
CALIBRATION_EMOTIONS = {"neutral", "emocionado", "asustado", "travieso"}
REVIEW_FIELDS = (
    "blind_code", "emotion", "intensity", "audio_file", "se_parece_a_daxter_1_5",
    "emocion_correcta_1_5", "naturalidad_1_5", "intensidad_correcta_1_5",
    "pronunciacion_1_5", "artefactos_1_5", "notas",
)


def force_offline_model_loading() -> None:
    """Bloquea cualquier acceso de Hugging Face antes de importar el motor."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def emotion_cases(catalog: dict) -> list[dict]:
    items = {item["id"]: item for item in catalog["emotions"]}
    cases = []
    for emotion in items:
        text = EMOTION_TEXTS[emotion]
        cases.extend((
            {"emotion": emotion, "intensity": "media", "reference_variant": "winner_diverse", "text": text},
            {"emotion": emotion, "intensity": "media", "reference_variant": "emotion_experimental", "text": text},
        ))
        if emotion in CALIBRATION_EMOTIONS:
            cases.extend((
                {"emotion": emotion, "intensity": "baja", "reference_variant": "winner_diverse", "text": text},
                {"emotion": emotion, "intensity": "alta", "reference_variant": "winner_diverse", "text": text},
            ))
    return cases


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def wav_metrics(path: Path, text: str) -> dict:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    values = array("h")
    if width == 2:
        values.frombytes(raw)
    mono = values[::channels] if values else []
    rms = math.sqrt(sum(value * value for value in mono) / len(mono)) if mono else 0
    dbfs = 20 * math.log10(rms / 32767) if rms else -120.0
    threshold = 32767 * (10 ** (-40 / 20))
    leading = next((index for index, value in enumerate(mono) if abs(value) > threshold), len(mono))
    trailing = next((index for index, value in enumerate(reversed(mono)) if abs(value) > threshold), len(mono))
    duration = frames / rate
    expected = max(0.8, len(text.split()) / 2.6)
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
        "sample_rate": rate, "channels": channels, "bits": width * 8,
        "audio_seconds": round(duration, 4), "rms_dbfs": round(dbfs, 4),
        "leading_silence_seconds": round(leading / rate, 4),
        "trailing_silence_seconds": round(trailing / rate, 4),
        "automatic_flags": flags,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def experimental_reference(item: dict, items: dict, audio_root: Path) -> Path:
    source = item
    if not source["reference_samples"]:
        source = items[source["fallback_emotion"]]
    if not source["reference_samples"]:
        source = items["neutral"]
    return audio_root / source["reference_samples"][0]["audio_file"]


def player_html(rows: list[dict]) -> str:
    sections = []
    for row in rows:
        sections.append(
            f'<article><h2>{html.escape(row["blind_code"])} · objetivo {html.escape(row["emotion"])} / {html.escape(row["intensity"])}</h2>'
            f'<audio controls preload="none" src="{html.escape(row["audio_file"])}"></audio></article>'
        )
    return """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prueba ciega de emociones Daxter</title><style>body{font-family:system-ui,sans-serif;max-width:1000px;margin:auto;padding:24px;background:#10131a;color:#f5f6fa}article{padding:14px;margin:12px 0;background:#1b2130;border:1px solid #38445e;border-radius:10px}audio{width:100%}h2{font-size:1rem;color:#ffb45b}</style></head><body><h1>Prueba emocional ciega</h1><p>La estrategia de referencia está oculta. Puntúa 5 como mejor; identidad Daxter tiene prioridad sobre dramatismo.</p>""" + "".join(sections) + "</body></html>"


def main() -> int:
    force_offline_model_loading()
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--winner-reference", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-flagged", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    items = {item["id"]: item for item in catalog["emotions"]}
    selector = VoiceStyleSelector(args.catalog)
    adapter = ChatterboxStyleAdapter(args.catalog, args.profile)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    started_init = time.perf_counter()
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    init_seconds = time.perf_counter() - started_init
    rows = []
    errors = []
    for index, case in enumerate(emotion_cases(catalog), 1):
        style = selector.resolve(case["emotion"], case["intensity"])
        tts_style = adapter.to_tts_style(style)
        reference = args.winner_reference if case["reference_variant"] == "winner_diverse" else experimental_reference(items[case["emotion"]], items, args.audio_root)
        folder = args.output_dir / case["emotion"]
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"E{index:03d}_{case['intensity']}_{case['reference_variant']}.wav"
        seed = adapter.stable_seed(args.seed, f"{style.style_key}:{case['reference_variant']}", case["text"])
        error = ""
        generation_seconds = 0.0
        if not (args.resume and output.is_file()):
            set_seed(seed)
            if device.type == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            try:
                audio = model.generate(
                    adapter.normalize_text(case["text"]), language_id=tts_style["language_id"],
                    audio_prompt_path=str(reference), exaggeration=tts_style["exaggeration"],
                    cfg_weight=tts_style["cfg_weight"], temperature=tts_style["temperature"],
                    repetition_penalty=tts_style["repetition_penalty"], min_p=tts_style["min_p"], top_p=tts_style["top_p"],
                )
                torchaudio.save(str(output), audio.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors.append({"case": index, "error": error})
            generation_seconds = time.perf_counter() - started
        metrics = wav_metrics(output, case["text"]) if output.is_file() else {}
        retry = None
        if args.retry_flagged and metrics.get("automatic_flags"):
            attempts = args.output_dir / "attempts"
            attempts.mkdir(exist_ok=True)
            original_attempt = attempts / f"E{index:03d}_original.wav"
            if not original_attempt.exists():
                shutil.copy2(output, original_attempt)
            retry_number = 1 + len(list(attempts.glob(f"E{index:03d}_retry*.wav")))
            retry_path = attempts / f"E{index:03d}_retry{retry_number}.wav"
            retry_seed = seed + retry_number * 1_000_000
            set_seed(retry_seed)
            retry_started = time.perf_counter()
            retry_audio = model.generate(
                adapter.normalize_text(case["text"]), language_id=tts_style["language_id"],
                audio_prompt_path=str(reference), exaggeration=tts_style["exaggeration"],
                cfg_weight=tts_style["cfg_weight"], temperature=tts_style["temperature"],
                repetition_penalty=tts_style["repetition_penalty"], min_p=tts_style["min_p"], top_p=tts_style["top_p"],
            )
            torchaudio.save(str(retry_path), retry_audio.cpu(), model.sr, encoding="PCM_S", bits_per_sample=16)
            retry_metrics = wav_metrics(retry_path, case["text"])
            retry = {
                "seed": retry_seed, "file": retry_path.relative_to(args.output_dir).as_posix(),
                "metrics": retry_metrics,
                "selected": (
                    len(retry_metrics["automatic_flags"]) < len(metrics["automatic_flags"])
                    or (
                        len(retry_metrics["automatic_flags"]) == len(metrics["automatic_flags"])
                        and retry_metrics["audio_seconds"] < metrics["audio_seconds"]
                    )
                ),
            }
            generation_seconds += time.perf_counter() - retry_started
            if retry["selected"]:
                shutil.copy2(retry_path, output)
                seed = retry_seed
                metrics = retry_metrics
        rows.append({
            "case_id": f"E{index:03d}", **case, "synthesis_text": adapter.normalize_text(case["text"]),
            "output_file": output.relative_to(args.output_dir).as_posix(), "reference_file": reference.name,
            "seed": seed, "generation_seconds": round(generation_seconds, 4), "error": error, "retry": retry, **metrics,
        })
    if errors:
        raise SystemExit(json.dumps(errors, ensure_ascii=False))

    blind_audio = args.output_dir / "blind_audio"
    blind_audio.mkdir(exist_ok=True)
    shuffled = rows[:]
    random.Random(args.seed).shuffle(shuffled)
    review_rows = []
    key = []
    for index, row in enumerate(shuffled, 1):
        code = f"EM{index:03d}"
        blind_file = blind_audio / f"{code}.wav"
        shutil.copy2(args.output_dir / row["output_file"], blind_file)
        review_rows.append({"blind_code": code, "emotion": row["emotion"], "intensity": row["intensity"], "audio_file": f"blind_audio/{blind_file.name}"})
        key.append({"blind_code": code, **row})
    review_rows.sort(key=lambda row: (row["emotion"], row["intensity"], row["blind_code"]))
    with (args.output_dir / "HUMAN_EMOTION_TEST.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)
    (args.output_dir / "EMOTION_TEST_KEY.json").write_text(json.dumps({"seed": args.seed, "entries": key}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "BLIND_EMOTION_PLAYER.html").write_text(player_html(review_rows), encoding="utf-8")
    manifest = {
        "winner_profile": "daxter_es_jak2", "cases": len(rows), "device": str(device),
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "initialization_seconds": round(init_seconds, 4), "errors": errors,
        "identity_policy": "winner_diverse active; emotion references experimental and blind",
        "laugh_policy": "short synthesized interjection; no long invented laugh or sample reuse",
        "rows": rows,
    }
    (args.output_dir / "EMOTION_LAB_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = {
        "wav": len(rows),
        "pcm16_mono": sum(row.get("bits") == 16 and row.get("channels") == 1 for row in rows),
        "automatic_anomalies": [
            {"case_id": row["case_id"], "emotion": row["emotion"], "flags": row["automatic_flags"]}
            for row in rows if row.get("automatic_flags")
        ],
        "intensity_calibration": {
            emotion: {
                row["intensity"]: row["rms_dbfs"]
                for row in rows
                if row["emotion"] == emotion and row["reference_variant"] == "winner_diverse"
            }
            for emotion in sorted(CALIBRATION_EMOTIONS)
        },
        "network_note": "The first 2026-08-11 run refreshed the official model cache; this runner now forces HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE.",
    }
    (args.output_dir / "EMOTION_LAB_VALIDATION.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sum_paths = sorted(path for path in args.output_dir.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt")
    (args.output_dir / "SHA256SUMS.txt").write_text("".join(f"{sha256_file(path)}  {path.relative_to(args.output_dir).as_posix()}\n" for path in sum_paths), encoding="utf-8")
    print(json.dumps({"cases": len(rows), "blind": len(review_rows), "errors": errors}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
