"""Puente JSON para ejecutar Kokoro desde su entorno Python 3.12.

Entrada por stdin:
{
  "text": "...",
  "voice": "em_alex",
  "output_path": "C:/ruta/salida.wav",
  "speed": 1.0,
  "volume": 1.0
}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


SAMPLE_RATE = 24_000


def main() -> int:
    payload = json.load(sys.stdin)

    text = str(payload["text"]).strip()
    voice = str(payload["voice"]).strip()
    output_path = Path(payload["output_path"])
    speed = float(payload.get("speed", 1.0))
    volume = float(payload.get("volume", 1.0))

    if not text:
        raise ValueError("El texto no puede estar vacío.")

    pipeline = KPipeline(lang_code="e")
    parts = [
        audio
        for _, _, audio in pipeline(
            text,
            voice=voice,
            speed=speed,
        )
    ]

    if not parts:
        raise RuntimeError("Kokoro no produjo audio.")

    audio = np.concatenate(parts) if len(parts) > 1 else parts[0]
    audio = np.clip(audio * volume, -1.0, 1.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, SAMPLE_RATE)

    print(
        json.dumps(
            {
                "success": True,
                "output_path": str(output_path),
                "voice": voice,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
