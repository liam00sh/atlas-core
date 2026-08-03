"""Reproducción local de archivos WAV."""

from __future__ import annotations

import os
from pathlib import Path


class WavePlayer:
    """Reproduce WAV de forma bloqueante en Windows."""

    def is_available(self) -> bool:
        return os.name == "nt"

    def play(self, path: Path) -> bool:
        if not self.is_available() or not path.exists():
            return False

        import winsound

        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME,
        )
        return True
