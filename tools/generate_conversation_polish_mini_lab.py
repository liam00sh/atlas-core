"""Genera 24 muestras B1 pequeñas; no selecciona ni publica un ganador."""

from __future__ import annotations

import argparse
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


POSTPROCESS = {
    "trim_start": False,
    "trim_end": True,
    "threshold": 0.0005,
    "end_padding_ms": 80,
    "ensure_end_padding": True,
    "fade_ms": 5,
}


def samples() -> list[dict[str, str]]:
    spanish = [
        "La acción está completada y la información también es correcta.",
        "Mañana revisaré la función y confirmaré que sigue activa.",
        "El acuario pequeño está encendido; la revisión termina aquí.",
        "Esta explicación contiene pronunciación, emoción y naturalidad.",
        "La primera opción es práctica y la segunda también funciona.",
        "Quiero una respuesta clara, completa y sin cortes al final.",
        "Atlas está listo para continuar con la conversación.",
        "La información esencial aparece antes de la conclusión.",
    ]
    rows = [
        {"category": "spanish_es", "variant": f"es_{index:02d}", "text": text}
        for index, text in enumerate(spanish, 1)
    ]
    terms = {
        "home_assistant": (
            "Home Assistant está conectado.",
            "La plataforma Home Assistant está conectada.",
            "Home Assistant, la plataforma domótica, está conectada.",
        ),
        "docker": (
            "Docker está funcionando.",
            "La plataforma Docker está funcionando.",
            "Docker, el motor de contenedores, está funcionando.",
        ),
        "telegram": (
            "Telegram está disponible.",
            "La aplicación Telegram está disponible.",
            "Telegram, la aplicación de mensajería, está disponible.",
        ),
    }
    for term, variants in terms.items():
        rows.extend(
            {"category": "english_terms", "variant": f"{term}_{index}", "text": text}
            for index, text in enumerate(variants, 1)
        )
    long = [
        "La primera idea termina aquí. La segunda añade un dato útil. La tercera cierra la respuesta sin enviar nada a la consola.",
        "Puedo darte una respuesta breve si la pides. En modo normal conservaré toda la explicación. Si quieres detalle, ampliaré cada punto.",
        "Primero comprobaré el estado real. Después explicaré el resultado. Por último indicaré con claridad cualquier dato que no haya podido verificar.",
        "Una respuesta larga se divide en unidades naturales. Mientras escuchas una, preparo la siguiente. Si cancelas, detengo el audio y vacío la cola.",
    ]
    rows.extend(
        {"category": "long_responses", "variant": f"long_{index}", "text": text}
        for index, text in enumerate(long, 1)
    )
    rows.extend((
        {"category": "conversation", "variant": "confirmation", "text": "He entendido: apaga la luz. ¿Es correcto?"},
        {"category": "conversation", "variant": "repeat", "text": "He oído una frase y he conservado la interpretación normalizada."},
        {"category": "conversation", "variant": "farewell", "text": "De acuerdo. Hasta luego; aquí estaré cuando vuelvas."},
    ))
    assert len(rows) == 24
    return rows


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
        postprocess_options=POSTPROCESS,
    )
    manifest = []
    try:
        for index, row in enumerate(samples(), 1):
            folder = args.output_dir / row["category"]
            folder.mkdir(parents=True, exist_ok=True)
            output = folder / f"{index:02d}_{row['variant']}.wav"
            if output.is_file() and output.stat().st_size > 44:
                with wave.open(str(output), "rb") as audio:
                    duration_ms = round(audio.getnframes() / audio.getframerate() * 1000, 3)
                manifest.append({
                    "index": index, **row,
                    "file": str(output.relative_to(args.output_dir)),
                    "success": True,
                    "error": None,
                    "latency_ms": 0.0,
                    "duration_ms": duration_ms,
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "reused": True,
                })
                continue
            started = perf_counter()
            result = provider.synthesize(SynthesisRequest(
                text=row["text"],
                voice_id="daxter_official",
                provider_voice_id="daxter_es_jak2",
                output_path=output,
                voice_profile_id="daxter_es_jak2",
                profile_version="1.0.0",
            ))
            record = {"index": index, **row, "file": str(output.relative_to(args.output_dir)), "success": result.success, "error": result.error, "latency_ms": round((perf_counter() - started) * 1000, 3)}
            if result.success:
                with wave.open(str(output), "rb") as audio:
                    record["duration_ms"] = round(audio.getnframes() / audio.getframerate() * 1000, 3)
                record["sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
            manifest.append(record)
    finally:
        provider.close()
    payload = {
        "schema_version": 1,
        "engine": "B1 legacy multilingual",
        "human_winner": None,
        "phase_6_closed": False,
        "count": len(manifest),
        "samples": manifest,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(item["success"] for item in manifest) else 2


if __name__ == "__main__":
    raise SystemExit(main())
