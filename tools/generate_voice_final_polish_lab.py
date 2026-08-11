"""Generate the private 40-audio final polish lab without selecting winners."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.models import SynthesisRequest
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter


SAFE_POSTPROCESS = {
    "trim_start": False,
    "trim_end": True,
    "threshold": 0.0005,
    "end_padding_ms": 80,
    "ensure_end_padding": True,
    "fade_ms": 5,
}


def _samples() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    spanish = {
        "accion": ("Acción completada.", "Ac-ción completada."),
        "funcion": ("La función está activa.", "La fun-ción está activa."),
        "esta": ("Atlas está listo.", "Atlas es-tá listo."),
        "pequeno": ("El acuario pequeño está encendido.", "El acuario pe-que-ño está encendido."),
        "manana": ("Mañana revisaré Atlas.", "Ma-ña-na revisaré Atlas."),
        "revision": ("La revisión está completa.", "La re-vi-sión está completa."),
        "tambien": ("También puedo ayudarte.", "Tam-bién puedo ayudarte."),
        "informacion": ("La información es correcta.", "La in-for-ma-ción es correcta."),
        "emocion": ("La emoción sigue siendo natural.", "La e-mo-ción sigue siendo natural."),
    }
    for sample, variants in spanish.items():
        for index, text in enumerate(variants, 1):
            rows.append({
                "folder": "pronunciation_es",
                "sample": sample,
                "variant": f"v{index}",
                "visible_text": variants[0],
                "tts_text": text,
                "postprocess": SAFE_POSTPROCESS,
            })

    english = {
        "home_assistant": ("Home Assistant", "Home Assístan", "Hom Assistant"),
        "docker": ("Docker", "Doc-ker", "Dóquer"),
        "telegram": ("Telegram", "Te-le-gram", "Telegrám"),
        "atlas": ("Atlas", "At-las", "Atlás"),
        "daxter": ("Daxter", "Dax-ter", "Daxter, listo para actuar"),
    }
    for sample, variants in english.items():
        for index, term in enumerate(variants, 1):
            rows.append({
                "folder": "english_terms",
                "sample": sample,
                "variant": f"v{index}",
                "visible_text": variants[0],
                "tts_text": f"{term} está conectado.",
                "postprocess": SAFE_POSTPROCESS,
            })

    edge_text = "Hola. Enciende la luz. Mañana revisaré Atlas."
    for fade_ms in (0, 5, 10, 15):
        rows.append({
            "folder": "trim_fade",
            "sample": "bordes",
            "variant": f"fade_{fade_ms}ms",
            "visible_text": edge_text,
            "tts_text": edge_text,
            "postprocess": {
                **SAFE_POSTPROCESS,
                "end_padding_ms": 0,
                "ensure_end_padding": False,
                "fade_ms": fade_ms,
            },
        })

    rows.extend((
        {
            "folder": "long_sentences",
            "sample": "resumen_completo",
            "variant": "segmentado",
            "visible_text": "Respuesta larga de consola",
            "tts_text": (
                "La respuesta completa aparece en la consola. "
                "Te resumo lo esencial sin dejar ninguna idea a medias."
            ),
            "postprocess": SAFE_POSTPROCESS,
        },
        {
            "folder": "long_sentences",
            "sample": "tres_unidades",
            "variant": "segmentado",
            "visible_text": "Tres unidades completas",
            "tts_text": (
                "La primera idea termina aquí. La segunda también queda completa. "
                "La tercera confirma que el audio ha llegado al final."
            ),
            "postprocess": SAFE_POSTPROCESS,
        },
        {
            "folder": "names",
            "sample": "daxter_atlas",
            "variant": "ortografia_original",
            "visible_text": "Daxter y Atlas",
            "tts_text": "Daxter está listo y Atlas también.",
            "postprocess": SAFE_POSTPROCESS,
        },
    ))
    if len(rows) != 40:
        raise RuntimeError(f"El laboratorio debe contener 40 audios, no {len(rows)}.")
    return rows


def _wav_metrics(path: Path) -> dict[str, object]:
    with wave.open(str(path), "rb") as audio:
        frames = audio.getnframes()
        rate = audio.getframerate()
        channels = audio.getnchannels()
        width = audio.getsampwidth()
    return {
        "frames": frames,
        "sample_rate": rate,
        "channels": channels,
        "sample_width": width,
        "duration_ms": round(frames / rate * 1000, 3),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    provider = ChatterboxDaxterProvider(
        worker_command=[str(args.python), str(ROOT / "tools" / "chatterbox_worker.py")],
        cache_dir=args.output_dir.parent / f"{args.output_dir.name}_cache",
        postprocess=True,
        postprocess_options=SAFE_POSTPROCESS,
    )
    manifest = []
    try:
        for index, row in enumerate(_samples(), 1):
            folder = args.output_dir / str(row["folder"])
            folder.mkdir(parents=True, exist_ok=True)
            output = folder / f"{index:02d}_{row['sample']}_{row['variant']}.wav"
            provider.postprocess_options = dict(row["postprocess"])
            started = perf_counter()
            result = provider.synthesize(SynthesisRequest(
                text=str(row["tts_text"]),
                voice_id="daxter_official",
                provider_voice_id="daxter_es_jak2",
                output_path=output,
                voice_profile_id="daxter_es_jak2",
                profile_version="1.0.0",
            ))
            record = {
                "index": index,
                **row,
                "file": str(output.relative_to(args.output_dir)),
                "success": result.success,
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "chars_sent_to_tts": len(str(row["tts_text"])),
                "normalized_tts_text": ChatterboxStyleAdapter.normalize_text(
                    str(row["tts_text"])
                ),
                "chars_synthesized": result.chars_synthesized,
                "error": result.error,
            }
            if result.success:
                record.update(_wav_metrics(output))
            manifest.append(record)
    finally:
        provider.close()

    (args.output_dir / "manifest.json").write_text(
        json.dumps({"count": len(manifest), "samples": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    fields = (
        "sample", "variante", "español_correcto_1_5", "pronunciacion_1_5",
        "sin_cortes_1_5", "naturalidad_1_5", "parecido_daxter_1_5",
        "preferencia", "notas",
    )
    with (args.output_dir / "HUMAN_FINAL_POLISH_REVIEW.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in manifest:
            writer.writerow({
                "sample": record["file"],
                "variante": record["variant"],
            })
    regression = (
        "Hola Daxter, ¿qué tal estás?", "¿Qué hora es?",
        "Enciende la luz del acuario pequeño.", "Apaga la luz del acuario pequeño.",
        "Dime algo divertido.", "Cuéntame un chiste.",
        "Estoy probando tu nueva voz.", "Reinicia Telegram.", "Cancelar.",
        "Cancelado.", "Recuérdame que mañana a las 18:30 tengo que revisar Atlas.",
        "Acción completada.", "La función está activa.",
        "Home Assistant está conectado.", "Docker está funcionando.",
        "Mañana revisaré Atlas.",
    )
    (args.output_dir / "E2E_REGRESSION_SCRIPT.txt").write_text(
        "\n".join(f"{index}. {text}" for index, text in enumerate(regression, 1)) + "\n",
        encoding="utf-8",
    )
    return 0 if all(item["success"] for item in manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
