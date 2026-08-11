"""Cola local cancelable; la síntesis nunca bloquea el núcleo por reproducción."""

from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import threading


class PlaybackQueue:
    def __init__(self, player) -> None:
        self.player = player
        self._queue: Queue[Path | None] = Queue()
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="atlas-playback", daemon=True)
        self._thread.start()

    def enqueue(self, path: Path) -> None:
        if self._closed.is_set():
            raise RuntimeError("La cola de reproducción está cerrada")
        self._queue.put(Path(path))

    def stop_current_audio(self) -> None:
        stop = getattr(self.player, "stop", None)
        if callable(stop):
            stop()

    def clear_queue(self) -> int:
        cleared = 0
        while True:
            try:
                item = self._queue.get_nowait()
            except Empty:
                return cleared
            else:
                self._queue.task_done()
                if item is not None:
                    cleared += 1

    def close(self) -> None:
        if self._closed.is_set():
            return
        self.stop_current_audio()
        self.clear_queue()
        self._closed.set()
        self._queue.put(None)
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._closed.is_set():
            path = self._queue.get()
            try:
                if path is None:
                    return
                self.player.play(path)
            finally:
                self._queue.task_done()
