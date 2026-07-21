"""Limitacion deslizante por usuario y chat."""

from collections import defaultdict, deque
from time import monotonic
import threading
from typing import Callable


class TelegramRateLimiter:
    def __init__(self, limit: int = 20, *, window_seconds: float = 60.0, clock: Callable[[], float] = monotonic) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, telegram_user_id: object, chat_id: object) -> bool:
        key = (str(telegram_user_id), str(chat_id))
        now = self.clock()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True
