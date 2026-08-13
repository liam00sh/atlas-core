"""PersonalityAdapter v2: reglas humanas, contexto y validación factual."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from conversation.response_models import BaseResponse, FactPreservationValidator, StyledResponse


class PersonalityStrength(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ResponseStyleContext:
    user: str = "REDACTED_2c7b6821719d"
    channel: str = "cli"
    request_type: str = "general"
    risk_level: str = "low"
    max_length: int = 500
    night_mode: bool = False
    suggested_emotion: str = "neutral"
    suggested_intensity: str = "media"
    personality_strength: PersonalityStrength = PersonalityStrength.NORMAL
    previous_styled_text: str = ""


PersonalityResult = StyledResponse


class ResponseStylePolicy:
    FORCED_PLAIN = {"privacy", "security", "emergency", "driving"}

    def resolve_strength(self, context: ResponseStyleContext) -> tuple[PersonalityStrength, str, bool]:
        request_type = context.request_type.casefold()
        risk = context.risk_level.casefold()
        if request_type == "emergency" or risk == "critical":
            return PersonalityStrength.LOW, "emergencia: claridad máxima", True
        if request_type in {"privacy", "security"} or risk == "high":
            return PersonalityStrength.LOW, "privacidad/seguridad: sin humor", True
        if request_type == "driving":
            return PersonalityStrength.LOW, "conducción: respuesta breve", True
        if context.night_mode and context.personality_strength == PersonalityStrength.HIGH:
            return PersonalityStrength.NORMAL, "modo nocturno: intensidad reducida", False
        return context.personality_strength, "nivel solicitado permitido por el contexto", False


class PersonalityAdapter:
    """Planifica movimientos de estilo; no selecciona respuestas completas."""

    _MARKERS = {
        "success": ("Hecho", "Bien", "Perfecto"),
        "action_result": ("Hecho", "Listo", "Bien"),
        "error": ("Vaya", "Uf", "Bueno"),
        "warning": ("Ojo", "Atención", "Eh"),
        "home_assistant": ("Hecho", "Listo", "Bien"),
        "greeting": ("Buenas", "Ey", "Hola"),
        "casual": ("Mira", "Bueno", "A ver"),
        "general": ("Mira", "Bien", "Ojo"),
    }
    _HIGH_MOVES = {
        "success": "Una tarea menos; seguimos.",
        "action_result": "Una misión resuelta; seguimos.",
        "error": "Toca otra vuelta, pero el estado queda claro.",
        "casual": "Ese plan sí tiene buena pinta.",
        "greeting": "Todo listo para movernos.",
        "general": "Lo importante queda claro; seguimos.",
    }
    def __init__(
        self,
        policy: ResponseStylePolicy | None = None,
        *,
        rules_path: Path | None = None,
        validator: FactPreservationValidator | None = None,
    ) -> None:
        self.policy = policy or ResponseStylePolicy()
        self.validator = validator or FactPreservationValidator()
        default_rules = Path(__file__).resolve().parent / "profiles" / "DAXTER_PERSONALITY_RULES_V2.json"
        selected = Path(rules_path) if rules_path else default_rules
        self.rules = json.loads(selected.read_text(encoding="utf-8")) if selected.is_file() else {}

    @staticmethod
    def _choice(options: tuple[str, ...], seed: int, key: str, previous: str) -> str:
        digest = hashlib.sha256(f"{seed}|{key}".encode("utf-8")).digest()
        start = int.from_bytes(digest[:4], "big") % len(options)
        for offset in range(len(options)):
            candidate = options[(start + offset) % len(options)]
            if not previous or candidate.casefold() not in previous.casefold():
                return candidate
        return options[start]

    @staticmethod
    def _join_short_clauses(text: str) -> str:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        if len(parts) < 2 or len(parts[0]) > 45 or len(parts[1]) > 70:
            return text
        first = parts[0].rstrip(".")
        second = parts[1]
        if second and second[0].islower():
            joined = f"{first}, {second}"
        elif second.split(" ", 1)[0] in {"El", "La", "Los", "Las", "Un", "Una"}:
            joined = f"{first}, {second[0].lower()}{second[1:]}"
        else:
            return text
        return " ".join((joined, *parts[2:])).strip()

    @staticmethod
    def _request_key(request_type: str) -> str:
        value = request_type.casefold()
        if value.startswith("home_assistant"):
            return "home_assistant"
        if value.startswith("accion_complet"):
            return "action_result"
        if value.startswith("accion_fall") or value.startswith("error"):
            return "error"
        if value.startswith("aviso"):
            return "warning"
        if value.startswith("saludo"):
            return "greeting"
        if value.startswith("casual") or value.startswith("broma"):
            return "casual"
        if value in PersonalityAdapter._MARKERS:
            return value
        return "general"

    @staticmethod
    def _lower_common_initial(text: str) -> str:
        match = re.match(
            r"^(El|La|Los|Las|Un|Una|Este|Esta|Esto|Queda|Quedan|Hay|Necesito|Podemos|No)\b",
            text,
        )
        if not match:
            return text
        return match.group(0).lower() + text[match.end():]

    def adapt(
        self,
        base_response: str | BaseResponse,
        context: ResponseStyleContext,
        *,
        seed: int = 0,
    ) -> StyledResponse:
        base = base_response if isinstance(base_response, BaseResponse) else BaseResponse.from_text(base_response)
        strength, reason, forced_plain = self.policy.resolve_strength(context)
        structured = "\n" in base.text and (
            len(base.text.splitlines()) >= 3
            or any(line.lstrip().startswith(("- ", "* ", "1. ", "```")) for line in base.text.splitlines())
        )
        if structured:
            forced_plain = True
            reason = "contenido estructurado: presentación conservada"
        if forced_plain:
            return StyledResponse(
                base.text, base.text, "neutral", "baja", strength.value, reason, True, ()
            )

        key = self._request_key(context.request_type)
        styled = self._join_short_clauses(base.text)
        # LOW significa claridad literal: sin prefijo, muletilla ni remate.
        use_marker = strength != PersonalityStrength.LOW
        if use_marker:
            marker = self._choice(
                self._MARKERS.get(key, self._MARKERS["general"]),
                seed,
                f"marker:{key}:{base.text}",
                context.previous_styled_text,
            )
            punctuation = "!" if key == "warning" and context.suggested_intensity == "alta" else ","
            styled = (
                f"¡{marker}! {styled}"
                if punctuation == "!"
                else f"{marker}, {self._lower_common_initial(styled)}"
            )

        if strength == PersonalityStrength.HIGH:
            move = self._HIGH_MOVES.get(key, self._HIGH_MOVES["general"])
            if move.casefold() not in context.previous_styled_text.casefold():
                styled = f"{styled} {move}"

        if len(styled) > context.max_length:
            styled = base.text
            reason += "; movimientos omitidos por límite de longitud"

        preserved, issues = self.validator.validate(base, styled)
        if not preserved:
            styled = base.text
            reason += "; fallback factual determinista"
            preserved, issues = self.validator.validate(base, styled)
        return StyledResponse(
            base_text=base.text,
            styled_text=styled,
            emotion=context.suggested_emotion,
            intensity=context.suggested_intensity,
            personality_strength=strength.value,
            reason=reason,
            facts_preserved=preserved,
            validation_issues=issues,
        )
