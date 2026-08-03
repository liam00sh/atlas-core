"""CLI local para consultar y cambiar preferencias de voz."""

from __future__ import annotations

import argparse
from pathlib import Path

from voice.models import AssistantIdentity
from voice.preferences.manager import VoicePreferenceManager


VALID_VOICES = {
    AssistantIdentity.DAXTER: {
        "daxter_official",
        "daxter_alex",
        "daxter_santa",
    },
    AssistantIdentity.COCO: {
        "coco_official",
        "coco_dora",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument(
        "--show",
        action="store_true",
    )
    parser.add_argument(
        "--identity",
        choices=("daxter", "coco"),
    )
    parser.add_argument("--voice")
    parser.add_argument(
        "--fallback",
        choices=("on", "off"),
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    manager = VoicePreferenceManager(
        storage_path=(
            project_root
            / "data"
            / "voice"
            / "user_preferences.json"
        ),
        user_provider=lambda: args.user,
    )

    if args.identity and args.voice:
        identity = AssistantIdentity(args.identity)
        if args.voice not in VALID_VOICES[identity]:
            allowed = ", ".join(sorted(VALID_VOICES[identity]))
            print(f"Voz no válida. Permitidas: {allowed}")
            return 1
        manager.set_voice(
            identity=identity,
            voice_id=args.voice,
        )

    if args.fallback:
        manager.set_fallback_enabled(
            args.fallback == "on"
        )

    preferences = manager.get_current()
    print(
        f"Usuario: {args.user}\n"
        f"Daxter: {preferences.daxter_voice_id}\n"
        f"Coco: {preferences.coco_voice_id}\n"
        f"Fallback: {preferences.fallback_enabled}\n"
        f"Velocidad: {preferences.speech_rate}\n"
        f"Volumen: {preferences.speech_volume}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
