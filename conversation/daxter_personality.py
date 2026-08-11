"""Adaptador offline y reversible: conserva QUÉ responde Atlas y limita CÓMO se expresa."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum


class PersonalityStrength(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ResponseStyleContext:
    user: str = "Alex"
    channel: str = "cli"
    request_type: str = "general"
    risk_level: str = "low"
    max_length: int = 500
    night_mode: bool = False
    suggested_emotion: str = "neutral"
    suggested_intensity: str = "media"
    personality_strength: PersonalityStrength = PersonalityStrength.NORMAL


@dataclass(frozen=True, slots=True)
class PersonalityResult:
    styled_text: str
    emotion: str
    intensity: str
    personality_strength_used: PersonalityStrength
    reason: str


class ResponseStylePolicy:
    SERIOUS_TYPES = {"privacy", "security", "emergency", "driving"}

    def resolve_strength(self, context: ResponseStyleContext) -> tuple[PersonalityStrength, str]:
        request_type = context.request_type.casefold()
        if request_type == "emergency" or context.risk_level.casefold() == "critical":
            return PersonalityStrength.LOW, "emergencia: claridad máxima y personalidad mínima"
        if request_type in {"privacy", "security"} or context.risk_level.casefold() == "high":
            return PersonalityStrength.LOW, "privacidad/seguridad: contenido sin humor"
        if request_type == "driving":
            return PersonalityStrength.LOW, "conducción: respuesta breve y no distractora"
        if context.night_mode and context.personality_strength == PersonalityStrength.HIGH:
            return PersonalityStrength.NORMAL, "modo nocturno: intensidad reducida"
        return context.personality_strength, "nivel solicitado permitido por el contexto"


class PersonalityAdapter:
    """Añade una marca breve original; nunca reescribe ni elimina la respuesta base."""

    PREFIXES = {
        "success": ("Hecho.", "Misión cumplida.", "Todo en orden."),
        "error": ("Bueno, esto necesita otra vuelta.", "Tenemos un contratiempo.", "El plan pide revisión."),
        "casual": ("Te diré una cosa:", "Mi lectura rápida:", "Vamos con ello:"),
        "greeting": ("¡Aquí estoy!", "¡Buenas!", "Listo para la misión."),
        "general": ("Vamos al grano:", "Bien, atención:", "Esto es lo importante:"),
    }
    HIGH_SUFFIXES = (
        "Ese es el plan; corto, claro y con una cantidad razonable de estilo.",
        "Y sí, podemos considerarlo una pequeña victoria del equipo.",
        "Nada mal para una misión que empezó sin explosiones.",
    )

    def __init__(self, policy: ResponseStylePolicy | None = None):
        self.policy = policy or ResponseStylePolicy()

    @staticmethod
    def _choice(options: tuple[str, ...], seed: int, key: str) -> str:
        digest = hashlib.sha256(f"{seed}|{key}".encode("utf-8")).digest()
        return options[int.from_bytes(digest[:4], "big") % len(options)]

    def adapt(self, base_response: str, context: ResponseStyleContext, *, seed: int = 0) -> PersonalityResult:
        base = str(base_response).strip()
        if not base:
            raise ValueError("La respuesta base no puede estar vacía")
        strength, reason = self.policy.resolve_strength(context)
        if strength == PersonalityStrength.LOW:
            return PersonalityResult(base, "neutral", "baja", strength, reason)

        request_type = context.request_type.casefold()
        prefix_key = request_type if request_type in self.PREFIXES else "general"
        prefix = self._choice(self.PREFIXES[prefix_key], seed, f"prefix:{prefix_key}:{base}")
        styled = f"{prefix} {base}"
        if strength == PersonalityStrength.HIGH and request_type in {"casual", "greeting", "success", "general"}:
            suffix = self._choice(self.HIGH_SUFFIXES, seed, f"suffix:{base}")
            styled = f"{styled} {suffix}"
        if len(styled) > context.max_length:
            styled = base
            reason += "; adorno omitido por límite de longitud"
        return PersonalityResult(
            styled_text=styled,
            emotion=context.suggested_emotion,
            intensity=context.suggested_intensity,
            personality_strength_used=strength,
            reason=reason,
        )
