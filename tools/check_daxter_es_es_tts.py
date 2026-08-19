"""Diagnóstico TTS es-ES aislado: rutas, carga, síntesis y altavoz."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import wave


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.chatterbox_es_es_runtime import resolve_es_es_model_dir
from voice.models import SynthesisRequest
from voice.player import WavePlayer
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider


CHECK_TEXT = "Hola, soy Daxter."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba exclusivamente la voz Daxter es-ES local, sin Atlas, STT ni Home Assistant."
    )
    parser.add_argument("--tts-python", type=Path, required=True)
    parser.add_argument("--tts-source", type=Path, required=True)
    parser.add_argument("--tts-model-dir", type=Path, required=True)
    parser.add_argument("--tts-reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-play", action="store_true", help=argparse.SUPPRESS)
    return parser


def validate_inputs(args: argparse.Namespace) -> list[str]:
    errors = []
    if not args.tts_python.is_file():
        errors.append(f"intérprete inexistente: {args.tts_python}")
    source_package = args.tts_source / "chatterbox" / "src" / "chatterbox" / "tts.py"
    if not source_package.is_file():
        errors.append(f"cargador es-ES inexistente: {source_package}")
    if not args.tts_reference.is_file():
        errors.append(f"referencia inexistente: {args.tts_reference}")
    else:
        try:
            with wave.open(str(args.tts_reference), "rb") as audio:
                if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                    errors.append(f"referencia WAV vacía: {args.tts_reference}")
        except (OSError, EOFError, wave.Error):
            errors.append(f"referencia WAV ilegible: {args.tts_reference}")
    route = resolve_es_es_model_dir(args.tts_model_dir)
    if not route.ready:
        errors.append(
            f"modelo incompleto en {route.effective}; faltan: {', '.join(route.missing_effective)}"
        )
    return errors


def run_check(args: argparse.Namespace, *, player=None) -> dict[str, object]:
    errors = validate_inputs(args)
    route = resolve_es_es_model_dir(args.tts_model_dir)
    report: dict[str, object] = {
        "success": False,
        "text": CHECK_TEXT,
        "provider": "Chatterbox Multilingual: Spanish (Spain)",
        "fallback": False,
        "offline": True,
        "paths": {
            "python": str(args.tts_python.resolve()),
            "source": str(args.tts_source.resolve()),
            "model_requested": str(route.requested),
            "model_effective": str(route.effective),
            "reference": str(args.tts_reference.resolve()),
            "output": str(args.output.resolve()),
        },
        "missing_requested": list(route.missing_requested),
        "errors": errors,
    }
    if errors:
        return report

    temporary_cache = tempfile.TemporaryDirectory(prefix="atlas_tts_check_")
    provider = ChatterboxDaxterProvider(
        candidate="es_es",
        source_path=args.tts_source,
        model_dir=args.tts_model_dir,
        reference_path=args.tts_reference,
        worker_command=[str(args.tts_python), str(ROOT / "tools" / "chatterbox_worker.py")],
        cache_dir=Path(temporary_cache.name),
    )
    try:
        result = provider.synthesize(SynthesisRequest(
            text=CHECK_TEXT,
            voice_id="daxter_official",
            provider_voice_id="daxter_es_jak2",
            output_path=args.output,
            emotion="neutral",
            intensity="baja",
            voice_profile_id="daxter_es_jak2",
            profile_version=str(provider.profile["version"]),
        ))
        report["runtime"] = provider.last_worker_diagnostics
        report["synthesis"] = {
            "success": result.success,
            "error": result.error,
            "wav_duration_ms": result.wav_duration_ms,
            "cache_hit": result.cache_hit,
        }
        if not result.success or result.output_path is None:
            report["errors"] = [result.error or "síntesis fallida"]
            return report
        playback = player or WavePlayer()
        played = True if args.no_play else playback.play(result.output_path)
        completed = True if args.no_play else bool(playback.last_playback_completed)
        report["playback"] = {"started": played, "completed": completed}
        report["success"] = bool(played and completed)
        if not report["success"]:
            report["errors"] = ["el WAV se generó, pero la reproducción no se completó"]
        return report
    finally:
        provider.close()
        temporary_cache.cleanup()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_check(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
