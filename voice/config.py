"""Configuración del subsistema de voz."""

from __future__ import annotations

import os
from pathlib import Path

VOICE_ENABLED = os.getenv("ATLAS_VOICE_ENABLED", "false").strip().lower() == "true"
KOKORO_COMMAND = os.getenv("ATLAS_KOKORO_COMMAND", "").strip()
VOICE_OUTPUT_DIR = Path(
    os.getenv("ATLAS_VOICE_OUTPUT_DIR", "runtime/voice")
).expanduser()
VOICE_PROVIDER_TIMEOUT_SECONDS = float(
    os.getenv("ATLAS_VOICE_PROVIDER_TIMEOUT_SECONDS", "90")
)
DAXTER_PREFERRED_VOICE = os.getenv(
    "ATLAS_DAXTER_VOICE",
    "daxter_official",
).strip()
COCO_PREFERRED_VOICE = os.getenv(
    "ATLAS_COCO_VOICE",
    "coco_official",
).strip()
VOICE_SPEAK_CONSOLE_OUTPUT = (
    os.getenv("ATLAS_VOICE_SPEAK_CONSOLE_OUTPUT", "true")
    .strip()
    .lower()
    == "true"
)
