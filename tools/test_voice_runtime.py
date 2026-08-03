"""Prueba manual de extremo a extremo del servicio de voz."""

from __future__ import annotations

import argparse

from voice.models import AssistantIdentity
from voice.service import VoiceService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--identity",
        choices=("daxter", "coco"),
        default="daxter",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Ejemplo: daxter_alex, daxter_santa o coco_dora.",
    )
    parser.add_argument(
        "text",
        nargs="?",
        default="Hola, REDACTED_2c7b6821719d. La voz alternativa de Atlas está funcionando.",
    )
    args = parser.parse_args()

    service = VoiceService()
    result = service.speak(
        args.text,
        identity=AssistantIdentity(args.identity),
        requested_voice_id=args.voice,
    )

    if result.success:
        print(f"Voz reproducida: {result.voice_id}")
        print(f"Archivo: {result.output_path}")
        return 0

    print(f"Error: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
