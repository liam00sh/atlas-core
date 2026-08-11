"""Reproducción local de archivos WAV."""

from __future__ import annotations

import os
from pathlib import Path
import threading


class WavePlayer:
    """Reproduce WAV de forma bloqueante en Windows."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        return os.name == "nt"

    def play(self, path: Path) -> bool:
        if not self.is_available() or not path.exists():
            return False

        import winsound

        with self._lock:
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return True

    def stop(self) -> None:
        if not self.is_available():
            return
        import winsound

        winsound.PlaySound(None, getattr(winsound, "SND_PURGE", 0))
