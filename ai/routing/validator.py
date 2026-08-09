"""Validación estructural; nunca confía en porcentajes declarados por un LLM."""
from __future__ import annotations

from dataclasses import dataclass
import re
from difflib import SequenceMatcher


@dataclass(frozen=True, slots=True)
class ValidationContext:
    question: str
    structured_facts_available: bool = False
    tool_executed: bool = False
    missing_required_data: bool = False
    recent_responses: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResponseValidation:
    sufficient: bool
    reason: str
    allow_fallback: bool = True
    safe_response: str | None = None


class ResponseValidator:
    ACTION_CLAIM = re.compile(
        r"\b(?:he|hemos)\s+(?:apagado|encendido|enviado|borrado|creado|ejecutado|cambiado)\b|"
        r"\b(?:listo|hecho),?\s+(?:ya\s+)?(?:está|esta)\b",
        re.IGNORECASE,
    )

    def validate(self, response: str, context: ValidationContext) -> ResponseValidation:
        clean = " ".join(str(response).split()).strip()
        if not clean:
            return ResponseValidation(False, "empty_response")
        if context.missing_required_data:
            admits_gap = bool(re.search(r"\b(no (?:lo )?sé|no tengo|no puedo confirmar|necesito que|puedes indicar)\b", clean, re.I))
            if not admits_gap:
                return ResponseValidation(
                    False,
                    "missing_information",
                    allow_fallback=False,
                    safe_response="No tengo información suficiente para afirmarlo. ¿Puedes darme el dato que falta?",
                )
        if self.ACTION_CLAIM.search(clean) and not context.tool_executed:
            return ResponseValidation(
                False,
                "unconfirmed_action_claim",
                allow_fallback=False,
                safe_response="No puedo afirmar que esa acción se haya realizado porque no tengo confirmación del componente responsable.",
            )
        if any(" ".join(previous.split()).casefold() == clean.casefold() for previous in context.recent_responses):
            return ResponseValidation(False, "literal_repetition")
        for previous in context.recent_responses[-3:]:
            if previous and SequenceMatcher(None, previous.casefold(), clean.casefold()).ratio() >= 0.92:
                return ResponseValidation(False, "near_repetition")
        if re.search(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", clean):
            return ResponseValidation(False, "unexpected_language")
        return ResponseValidation(True, "sufficient")

