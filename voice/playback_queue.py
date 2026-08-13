"""Cola local cancelable; la síntesis nunca bloquea el núcleo por reproducción."""

from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import threading
from dataclasses import dataclass, field


@dataclass(slots=True)
class PlaybackTicket:
    completed: bool | None = None
    interrupted: bool = False
    duration_ms: float = 0.0
    _done: threading.Event = field(default_factory=threading.Event, repr=False)

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)


@dataclass(slots=True)
class _PlaybackItem:
    path: Path
    ticket: PlaybackTicket


class PlaybackQueue:
    def __init__(self, player) -> None:
        self.player = player
        self._queue: Queue[_PlaybackItem | None] = Queue()
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="atlas-playback", daemon=True)
        self._thread.start()

    def enqueue(self, path: Path) -> PlaybackTicket:
        if self._closed.is_set():
            raise RuntimeError("La cola de reproducción está cerrada")
        ticket = PlaybackTicket()
        self._queue.put(_PlaybackItem(Path(path), ticket))
        return ticket

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
                    item.ticket.interrupted = True
                    item.ticket.completed = False
                    item.ticket._done.set()
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
            item = self._queue.get()
            try:
                if item is None:
                    return
                played = bool(self.player.play(item.path))
                item.ticket.duration_ms = float(
                    getattr(self.player, "last_playback_duration_ms", 0.0)
                )
                item.ticket.interrupted = bool(
                    getattr(self.player, "last_playback_interrupted", False)
                )
                item.ticket.completed = bool(
                    played and getattr(self.player, "last_playback_completed", True)
                )
            finally:
                if item is not None:
                    item.ticket._done.set()
                self._queue.task_done()
