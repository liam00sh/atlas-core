"""Reproducción local de archivos WAV."""

from __future__ import annotations

import os
from pathlib import Path
import threading
from time import perf_counter
import wave


class WavePlayer:
    """Reproduce WAV de forma bloqueante en Windows."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._interrupt_requested = threading.Event()
        self.last_playback_duration_ms = 0.0
        self.last_playback_completed = False
        self.last_playback_interrupted = False

    def is_available(self) -> bool:
        return os.name == "nt"

    def play(self, path: Path) -> bool:
        if not self.is_available() or not path.exists():
            return False

        import winsound

        try:
            with wave.open(str(path), "rb") as audio:
                expected_ms = audio.getnframes() / float(audio.getframerate()) * 1000
        except (OSError, EOFError, wave.Error, ZeroDivisionError):
            return False

        self._interrupt_requested.clear()
        started = perf_counter()
        with self._lock:
            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        elapsed_ms = (perf_counter() - started) * 1000
        interrupted = self._interrupt_requested.is_set()
        self.last_playback_duration_ms = round(elapsed_ms, 3)
        self.last_playback_interrupted = interrupted
        self.last_playback_completed = bool(
            not interrupted and elapsed_ms >= max(0.0, expected_ms - 120.0)
        )
        return True

    def stop(self) -> None:
        if not self.is_available():
            return
        import winsound

        self._interrupt_requested.set()
        winsound.PlaySound(None, getattr(winsound, "SND_PURGE", 0))
