"""Consola manual de voz Daxter para PC, sin escucha continua."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import build_atlas
from voice.end_to_end import ManualVoiceSession
from voice.microphone import ManualMicrophoneRecorder
from voice.service import VoiceService
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService


def main() -> int:
    parser = argparse.ArgumentParser(description="Habla manualmente con Daxter usando micrófono local.")
    parser.add_argument("--list-devices", action="store_true", help="Muestra los micrófonos detectados y termina.")
    parser.add_argument("--device", help="Nombre exacto del micrófono de Windows.")
    args = parser.parse_args()
    recorder = ManualMicrophoneRecorder(device_name=args.device)
    if args.list_devices:
        for device in recorder.list_devices():
            print(device)
        return 0
    config = STTConfig.from_env()
    stt = STTService(
        FasterWhisperSTTProvider(config),
        AudioConverter(timeout_seconds=min(30.0, config.timeout_seconds)),
        config=config,
        work_dir=ROOT / "runtime" / "voice" / "stt",
    )
    session = ManualVoiceSession(
        atlas=build_atlas(),
        recorder=recorder,
        stt=stt,
        voice_service=VoiceService(),
        work_dir=ROOT / "runtime" / "voice" / "input",
    )
    print(f"Micrófono: {recorder.selected_device()}")
    print("Modo manual: Atlas solo graba entre las dos pulsaciones de Enter. Ctrl+C cancela.")
    try:
        running = True
        while running:
            result = session.capture_turn()
            print(f"Tú: {result.transcript}")
            if result.response:
                print(f"Daxter: {result.response}")
            print("Latencias (ms): " + ", ".join(f"{key}={value:.1f}" for key, value in result.timings_ms.items()))
            if result.synthesis is not None and not result.synthesis.success:
                print(f"Voz no disponible; respuesta conservada en texto: {result.synthesis.error}")
            running = result.continue_running
    except KeyboardInterrupt:
        print("\nTurno cancelado.")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
