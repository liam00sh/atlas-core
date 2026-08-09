"""Estado conversacional explícito compartido por CLI, Telegram y voz."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
import threading


@dataclass(slots=True)
class ConversationState:
    session_id: str
    channel: str
    authenticated_identity: str
    conversational_identity: str
    topic: str | None = None
    recent_entities: list[str] = field(default_factory=list)
    pending_references: list[str] = field(default_factory=list)
    known_location: str | None = None
    habitual_residence: str | None = None
    temporary_location: str | None = None
    home_presence: str = "unknown"
    relevant_time: str | None = None
    recent_actions: list[dict[str, object]] = field(default_factory=list)
    pending_actions: list[dict[str, object]] = field(default_factory=list)
    pending_confirmations: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    temporary_facts: dict[str, str] = field(default_factory=dict)
    shared_participants: list[str] = field(default_factory=list)
    ai_override: str = "auto"
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ConversationManager:
    """Mantiene estado semántico sin convertir inferencias en verdad persistente."""

    def __init__(self) -> None:
        self._states: dict[str, ConversationState] = {}
        self._active_key: str | None = None
        self._lock = threading.RLock()

    @staticmethod
    def key(channel: str, session_id: str, authenticated_identity: str) -> str:
        return ":".join((str(channel).casefold(), str(session_id).casefold(), str(authenticated_identity).casefold()))

    def begin_turn(
        self,
        *,
        channel: str,
        session_id: str,
        authenticated_identity: str,
        conversational_identity: str | None = None,
    ) -> ConversationState:
        key = self.key(channel, session_id, authenticated_identity)
        with self._lock:
            state = self._states.get(key)
            if state is None:
                state = ConversationState(
                    session_id=str(session_id),
                    channel=str(channel),
                    authenticated_identity=str(authenticated_identity),
                    conversational_identity=str(conversational_identity or authenticated_identity),
                )
                self._states[key] = state
            else:
                state.conversational_identity = str(conversational_identity or state.conversational_identity)
            state.updated_at = datetime.now(UTC).isoformat()
            self._active_key = key
            return state

    def current(self) -> ConversationState | None:
        with self._lock:
            return self._states.get(self._active_key or "")

    def observe_user_message(self, text: str) -> ConversationState | None:
        state = self.current()
        if state is None:
            return None
        clean = " ".join(str(text).split()).strip()
        lowered = clean.casefold()
        location_match = re.search(
            r"(?:he venido|estoy)\s+(?:a|en)\s+(casa\s+de\s+[^.,;!?]+?)(?:\s+unos?\s+d[ií]as|\s+un\s+tiempo|[.,;!?]|$)",
            lowered,
        )
        if location_match:
            location = location_match.group(1).strip()
            state.temporary_location = location
            state.known_location = location
            state.temporary_facts["location"] = location
            # Una declaración de ubicación no prueba presencia domótica.
        reference_words = re.findall(r"\b(?:esa|ese|eso|él|ella|la anterior|lo anterior)\b", lowered)
        state.pending_references = list(dict.fromkeys(reference_words))[-6:]
        state.updated_at = datetime.now(UTC).isoformat()
        return state

    def set_habitual_residence(self, value: str | None, *, verified: bool) -> None:
        state = self.current()
        if state is not None and verified:
            state.habitual_residence = str(value).strip() if value else None

    def set_temporary_location(self, value: str | None) -> None:
        state = self.current()
        if state is not None:
            state.temporary_location = str(value).strip() if value else None
            state.known_location = state.temporary_location or state.habitual_residence

    def set_home_presence(self, value: str) -> None:
        state = self.current()
        if state is None:
            return
        normalized = str(value or "unknown").strip().casefold()
        state.home_presence = (
            normalized
            if normalized in {"home_verified", "away_verified"}
            else "unknown"
        )

    def record_tool(self, name: str) -> None:
        state = self.current()
        if state is not None and name not in state.tools_used:
            state.tools_used.append(str(name))
            state.tools_used[:] = state.tools_used[-12:]

    def record_action(self, decision: dict[str, object]) -> None:
        state = self.current()
        if state is not None:
            state.recent_actions.append(dict(decision))
            state.recent_actions[:] = state.recent_actions[-12:]

    def set_ai_override(self, role: str) -> str:
        normalized = str(role or "auto").strip().casefold()
        if normalized not in {"auto", "fast", "reasoning", "deep"}:
            raise ValueError("El modo de IA debe ser auto, fast, reasoning o deep.")
        state = self.current()
        if state is None:
            raise RuntimeError("No existe una sesión conversacional activa.")
        state.ai_override = normalized
        state.updated_at = datetime.now(UTC).isoformat()
        return normalized

    def get_ai_override(self) -> str:
        state = self.current()
        return state.ai_override if state is not None else "auto"

    def prompt_context(self) -> str:
        state = self.current()
        if state is None:
            return ""
        return "\n".join(
            [
                "ESTADO CONVERSACIONAL ESTRUCTURADO (no concede permisos)",
                f"Canal: {state.channel}",
                f"Identidad autenticada: {state.authenticated_identity}",
                f"Interlocutor: {state.conversational_identity}",
                f"Tema: {state.topic or 'no fijado'}",
                f"Ubicación contextual actual: {state.known_location or 'no confirmada'}",
                f"Domicilio habitual verificado: {state.habitual_residence or 'no disponible'}",
                f"Ubicación temporal: {state.temporary_location or 'ninguna'}",
                f"Presencia doméstica verificada: {state.home_presence}",
                "No confundas identidad, cuenta, domicilio, ubicación temporal ni presencia doméstica.",
            ]
        )
