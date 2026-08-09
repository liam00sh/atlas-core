"""Redacción contextual breve con historial anti-repetición."""
from __future__ import annotations

from datetime import datetime
import hashlib
import itertools


class ContextualMessageGenerator:
    """Compone mensajes a partir del contexto, sin una lista de frases completas."""

    OPENINGS = {
        "started": ("Ya estoy disponible", "He vuelto a estar operativo", "Atlas vuelve a estar listo"),
        "stopping": ("Voy a detenerme", "Atlas se desconecta por ahora", "Cierro de forma segura"),
        "progress": ("Sigo con ello", "Estoy revisando la información", "La consulta continúa en proceso"),
        "completed": ("Listo", "Operación completada", "Ya está terminado"),
        "failed": ("No ha salido bien", "La operación ha fallado", "No he podido completarlo"),
    }
    CONTEXT = {
        "morning": ("esta mañana", "para empezar el día"),
        "afternoon": ("esta tarde", "para continuar"),
        "evening": ("esta noche", "cuando quieras"),
    }

    def __init__(self, max_recent: int = 8) -> None:
        self.max_recent = max(2, int(max_recent))
        self._recent: dict[str, list[str]] = {}

    @staticmethod
    def period(hour: int) -> str:
        return "morning" if hour < 13 else "afternoon" if hour < 21 else "evening"

    def generate(
        self,
        event: str,
        *,
        user: str,
        assistant: str,
        channel: str,
        situation: str | None = None,
        hour: int | None = None,
        recent: tuple[str, ...] = (),
    ) -> str:
        hour = datetime.now().hour if hour is None else int(hour)
        period = self.period(hour)
        openings = self.OPENINGS.get(event, ("Estoy aquí",))
        contexts = self.CONTEXT[period]
        endings = (
            f"{user}, podemos continuar.",
            "Dime qué necesitas.",
            f"Canal {channel} preparado.",
        )
        candidates = []
        for opening, context, ending in itertools.product(openings, contexts, endings):
            subject = opening.replace("Atlas", assistant)
            middle = f" {context}" if event in {"started", "progress"} else ""
            detail = f": {situation.strip()}" if situation else ""
            candidates.append(f"{subject}{middle}{detail}. {ending}")

        key = f"{event}:{user.casefold()}:{channel.casefold()}"
        blocked = {item.strip().casefold() for item in (*self._recent.get(key, []), *recent) if item.strip()}
        available = [item for item in candidates if item.casefold() not in blocked] or candidates
        seed = f"{event}|{user}|{assistant}|{channel}|{hour}|{len(blocked)}"
        index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(available)
        selected = available[index]
        self._recent.setdefault(key, []).append(selected)
        self._recent[key] = self._recent[key][-self.max_recent:]
        return selected

