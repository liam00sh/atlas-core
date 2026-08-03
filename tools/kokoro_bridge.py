"""Puente JSON para ejecutar Kokoro desde su entorno Python 3.12."""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Permite importar el paquete ``voice`` aunque este archivo se ejecute
# directamente con el Python externo del laboratorio de Kokoro.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import numpy as np
import soundfile as sf
from kokoro import KPipeline

from voice.prosody import segment_text


SAMPLE_RATE = 24_000


def _silence(duration_ms: int) -> np.ndarray:
    frames = int(SAMPLE_RATE * duration_ms / 1000)
    return np.zeros(frames, dtype=np.float32)


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
    final_parts: list[np.ndarray] = []

    for segment in segment_text(text):
        audio_parts = [
            audio
            for _, _, audio in pipeline(
                segment.text,
                voice=voice,
                speed=speed,
            )
        ]

        if not audio_parts:
            continue

        segment_audio = (
            np.concatenate(audio_parts)
            if len(audio_parts) > 1
            else audio_parts[0]
        )
        final_parts.append(segment_audio)

        if segment.pause_after_ms > 0:
            final_parts.append(
                _silence(segment.pause_after_ms)
            )

    if not final_parts:
        raise RuntimeError("Kokoro no produjo audio.")

    audio = np.concatenate(final_parts)
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
