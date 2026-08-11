"""Consola manual de voz Daxter para PC, sin escucha continua."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import build_atlas
from automation.home_assistant_factory import load_env_file
from voice.end_to_end import ManualVoiceSession
from voice.microphone import ManualMicrophoneRecorder
from voice.service import VoiceService
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService


def choose_microphone(recorder: ManualMicrophoneRecorder, *, input_func=input) -> str:
    if recorder.device_name:
        return recorder.device_name
    devices = recorder.list_devices()
    if not devices:
        return recorder.selected_device()
    if len(devices) == 1:
        recorder.device_name = devices[0]
        return devices[0]
    print("Micrófonos detectados:")
    for index, device in enumerate(devices, 1):
        print(f"  {index}. {device}")
    while True:
        selected = input_func("Elige el número de los cascos Bluetooth: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(devices):
            recorder.device_name = devices[int(selected) - 1]
            return recorder.device_name
        print("Selección no válida.")


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Habla manualmente con Daxter usando micrófono local.")
    parser.add_argument("--list-devices", action="store_true", help="Muestra los micrófonos detectados y termina.")
    parser.add_argument("--device", help="Nombre exacto del micrófono de Windows.")
    parser.add_argument(
        "--home-assistant-env",
        type=Path,
        help="Archivo privado .env para usar el mismo Home Assistant que Telegram.",
    )
    args = parser.parse_args()
    if args.home_assistant_env:
        if not args.home_assistant_env.is_file():
            parser.error("El archivo privado de Home Assistant no existe.")
        os.environ.update(load_env_file(args.home_assistant_env))
    recorder = ManualMicrophoneRecorder(device_name=args.device)
    if args.list_devices:
        for device in recorder.list_devices():
            print(device)
        return 0
    selected_device = choose_microphone(recorder)
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
    print(f"Micrófono: {selected_device}")
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
