"""Métricas efímeras por petición, sin contenido ni datos personales."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Iterator


_CURRENT: ContextVar["RequestTiming | None"] = ContextVar("atlas_request_timing", default=None)


@dataclass
class RequestTiming:
    values_ms: dict[str, float] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def add(self, name: str, seconds: float) -> None:
        with self._lock:
            self.values_ms[name] = round(self.values_ms.get(name, 0.0) + seconds * 1000, 3)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return dict(self.values_ms)


def bind_request_timing(timing: RequestTiming) -> Token:
    return _CURRENT.set(timing)


def reset_request_timing(token: Token) -> None:
    _CURRENT.reset(token)


def record_stage_duration(name: str, seconds: float) -> None:
    timing = _CURRENT.get()
    if timing is not None:
        timing.add(name, seconds)


@contextmanager
def measure_stage(name: str) -> Iterator[None]:
    timing = _CURRENT.get()
    if timing is None:
        yield
        return
    started = perf_counter()
    try:
        yield
    finally:
        timing.add(name, perf_counter() - started)
