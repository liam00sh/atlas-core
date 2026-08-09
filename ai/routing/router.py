"""Router explicable de modelos locales basado en señales combinadas."""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata

from ai.models.roles import ModelRole


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]+", " ", value)).strip()


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    message: str
    intent: str = "conversation"
    context_messages: int = 0
    retrieved_items: int = 0
    memory_required: bool = False
    relationship_reasoning: bool = False
    tools_required: bool = False
    temporal_reasoning: bool = False
    operation_criticality: int = 0
    deterministic_possible: bool = False
    has_contradictions: bool = False
    override: str = "auto"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    role: ModelRole
    reasons: tuple[str, ...]
    score: int
    overridden: bool = False

    @property
    def reason(self) -> str:
        return "+".join(self.reasons) or "simple"


class AIRouter:
    """Combina intención, estado, ambigüedad, herramientas y criticidad."""

    VALID_OVERRIDES = {"auto", "fast", "reasoning", "deep"}

    def __init__(self, override: str | None = None) -> None:
        selected = str(override or os.getenv("ATLAS_AI_ROUTE", "auto")).strip().casefold()
        if selected not in self.VALID_OVERRIDES:
            raise ValueError("ATLAS_AI_ROUTE debe ser auto, fast, reasoning o deep.")
        self.override = selected

    @staticmethod
    def _signals(request: RoutingRequest) -> tuple[int, list[str]]:
        text = _plain(request.message)
        original = str(request.message).casefold()
        score = 0
        reasons: list[str] = []

        references = bool(
            re.search(r"\b(esa|ese|eso|ella|lo anterior|la anterior|antes|aquello)\b", text)
            or re.search(r"\bél\b", original)
        )
        ambiguous = references or bool(re.search(r"\b(alguien|algo|alli|aqui|entonces|como eso)\b", text))
        multi_step = bool(re.search(r"\b(primero|despues|luego|compara|planifica|paso a paso|teniendo en cuenta)\b", text))
        technical = request.intent in {"technical_analysis", "planning"}

        def add(points: int, reason: str, condition: bool) -> None:
            nonlocal score
            if condition:
                score += points
                reasons.append(reason)

        add(2, "context", request.context_messages >= 2)
        add(2, "references", references)
        add(2, "ambiguity", ambiguous)
        add(3, "memory", request.memory_required)
        add(3, "relationships", request.relationship_reasoning)
        add(2, "multi_step", multi_step)
        add(2, "tools", request.tools_required)
        add(2, "temporal", request.temporal_reasoning)
        add(min(4, max(0, request.operation_criticality)), "critical", request.operation_criticality > 0)
        add(2, "retrieval", request.retrieved_items >= 4)
        add(4, "large_retrieval", request.retrieved_items >= 10)
        add(5, "contradictions", request.has_contradictions)
        add(3, "technical", technical)
        add(2, "long_context", request.context_messages >= 8)
        if request.deterministic_possible:
            score -= 4
            reasons.append("deterministic")
        return score, reasons

    def route(self, request: RoutingRequest) -> RouteDecision:
        requested_override = str(request.override or "auto").strip().casefold()
        override = self.override if requested_override == "auto" else requested_override
        if override not in self.VALID_OVERRIDES:
            raise ValueError("Override de IA no válido.")
        if override != "auto":
            return RouteDecision(ModelRole(override), ("manual_override",), 0, overridden=True)

        score, reasons = self._signals(request)
        if request.has_contradictions or score >= 13:
            role = ModelRole.DEEP
        elif score >= 4:
            role = ModelRole.REASONING
        else:
            role = ModelRole.FAST
        return RouteDecision(role, tuple(dict.fromkeys(reasons)) or ("simple",), score)
