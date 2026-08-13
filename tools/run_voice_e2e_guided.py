"""Recorrido E2E de voz manual con guardado incremental privado."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import build_atlas
from automation.home_assistant_factory import load_env_file
from tools.run_daxter_voice_pc import choose_microphone
from voice.end_to_end import ManualVoiceSession
from voice.microphone import ManualMicrophoneRecorder
from voice.service import VoiceService
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService


PHRASE_TEMPLATES = (
    "Hola Daxter, ¿qué tal estás?", "¿Qué hora es?", "Repite.", "Dime algo divertido.",
    "Saluda a {known_name}.", "Enciende la luz del acuario pequeño.", "Apaga la luz del acuario pequeño.",
    "Recuérdame mañana a las 18:30 que revise Atlas.", "Reinicia Telegram.", "Cancelar.",
    "¿Docker está funcionando?", "Home Assistant está conectado.", "Hasta luego.",
)


def phrases(*, known_name: str = "persona conocida") -> tuple[str, ...]:
    return tuple(phrase.format(known_name=known_name) for phrase in PHRASE_TEMPLATES)


def save(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home-assistant-env", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device")
    parser.add_argument("--known-name", default="persona conocida")
    args = parser.parse_args()
    if not args.home_assistant_env.is_file():
        parser.error("No existe el .env privado de Home Assistant.")
    os.environ.update(load_env_file(args.home_assistant_env))
    recorder = ManualMicrophoneRecorder(device_name=args.device)
    selected = choose_microphone(recorder)
    config = STTConfig.from_env()
    stt = STTService(FasterWhisperSTTProvider(config), AudioConverter(timeout_seconds=min(30, config.timeout_seconds)), config=config, work_dir=args.output.parent / "e2e_audio_converted")
    session = ManualVoiceSession(atlas=build_atlas(), recorder=recorder, stt=stt, voice_service=VoiceService(), work_dir=args.output.parent / "e2e_audio")
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "microphone": selected, "completed": False, "cases": [],
        "validation_dimensions": ["naturalidad", "confirmaciones", "repeat", "contexto", "grounding", "recordatorios", "home_assistant", "cancelación", "stt", "tts"],
    }
    print("Prueba guiada real. Lee una frase por turno; no adelantes 'Cancelar' antes de que Atlas pida confirmación.")
    guided_phrases = phrases(known_name=args.known_name)
    try:
        for index, phrase in enumerate(guided_phrases, 1):
            print(f"\nCaso {index}/{len(guided_phrases)}. Di exactamente:\n\"{phrase}\"")
            result = session.capture_turn()
            case = {
                "index": index, "expected_phrase": phrase, "transcript": result.transcript,
                "response": result.response, "continue_running": result.continue_running,
                "timings_ms": result.timings_ms,
                "tts_success": result.synthesis.success if result.synthesis else None,
                "human_correct": input("¿Resultado correcto? [s/n/parcial]: ").strip().casefold(),
                "naturalness_1_5": input("Naturalidad de voz [1-5 o vacío]: ").strip(),
                "physical_observation": input("Observación física/UI si aplica: ").strip(),
                "notes": input("Notas: ").strip(),
            }
            report["cases"].append(case)
            save(args.output, report)
        report["completed"] = True
        save(args.output, report)
    finally:
        session.close()
    print(f"Informe: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
