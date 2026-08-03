"""Configuración del subsistema de voz.

Kokoro se ejecutará fuera del proceso principal de Atlas Core para mantener
aislado su entorno Python 3.12 del núcleo Python 3.14.
"""

from __future__ import annotations

import os
from pathlib import Path

VOICE_ENABLED = os.getenv("ATLAS_VOICE_ENABLED", "false").strip().lower() == "true"
KOKORO_COMMAND = os.getenv("ATLAS_KOKORO_COMMAND", "").strip()
VOICE_OUTPUT_DIR = Path(
    os.getenv("ATLAS_VOICE_OUTPUT_DIR", "runtime/voice")
).expanduser()
VOICE_PROVIDER_TIMEOUT_SECONDS = float(
    os.getenv("ATLAS_VOICE_PROVIDER_TIMEOUT_SECONDS", "45")
)
