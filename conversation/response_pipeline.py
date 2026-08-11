"""Una única política de personalidad y emoción para todos los canales."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from conversation.daxter_personality import (
    PersonalityAdapter,
    PersonalityStrength,
    ResponseStyleContext,
)
from conversation.response_models import BaseResponse, StyledResponse
from voice.style import VoiceStyleSelector


@dataclass(frozen=True, slots=True)
class EmotionIntent:
    emotion: str
    intensity: str
    reason: str


class EmotionResolver:
    """Deriva intención acústica del resultado, nunca hechos nuevos."""

    def resolve(self, request_type: str, text: str, risk_level: str = "low") -> EmotionIntent:
        key = request_type.casefold()
        normalized = text.casefold()
        if key in {"privacy", "security", "driving", "emergency"} or risk_level in {"high", "critical"}:
            return EmotionIntent("neutral", "baja", "contexto sensible")
        if key in {"success", "action_result"} or any(word in normalized for word in ("correctamente", "completad", "terminó", "consegu")):
            return EmotionIntent("emocionado", "media", "resultado positivo")
        if key == "error" or any(word in normalized for word in ("error", "falló", "no pudo", "no se envió")):
            return EmotionIntent("determinado", "media", "error operativo controlado")
        if key == "warning" or any(word in normalized for word in ("aviso", "atención", "batería", "alerta")):
            return EmotionIntent("sorprendido", "media", "aviso contextual")
        if key == "greeting":
            return EmotionIntent("sonriente", "media", "saludo")
        if key in {"casual", "humour"}:
            return EmotionIntent("picaro", "media", "conversación casual")
        if key in {"question", "technical"}:
            return EmotionIntent("curioso", "media", "consulta")
        return EmotionIntent("neutral", "media", "respuesta general")


class DaxterResponsePipeline:
    def __init__(
        self,
        *,
        personality: PersonalityAdapter | None = None,
        emotion_resolver: EmotionResolver | None = None,
        style_selector: VoiceStyleSelector | None = None,
    ) -> None:
        root = Path(__file__).resolve().parent.parent
        self.personality = personality or PersonalityAdapter()
        self.emotion_resolver = emotion_resolver or EmotionResolver()
        self.style_selector = style_selector or VoiceStyleSelector(
            root / "voice_profiles" / "DAXTER_EMOTION_CATALOG_FINAL.json"
        )

    @staticmethod
    def infer_request_type(text: str, request_text: str = "") -> str:
        combined = f"{request_text} {text}".casefold()
        patterns = (
            ("emergency", r"\b(112|emergencia|humo|incendio|cable eléctrico)\b"),
            ("privacy", r"\b(privad[oa]|conversación de otro|datos personales)\b"),
            ("security", r"\b(permiso|autorización|bloquead[oa]|validación|confirmación explícita)\b"),
            ("driving", r"\b(gira|carril|kilómetro|conducción|carretera)\b"),
            ("error", r"\b(error|falló|fallo|no pude|no pudo|no se envió|caducó)\b"),
            ("success", r"\b(correctamente|completad[oa]|terminó|hecho|conseguimos)\b"),
            ("warning", r"\b(aviso|alerta|atención|batería)\b"),
            ("greeting", r"\b(hola|buenas noches|buenos días)\b"),
            ("home_assistant", r"\b(home assistant|luz|termostato)\b"),
            ("technical", r"\b(commit|rama|latencia|megabytes|proceso|servicio)\b"),
        )
        return next((kind for kind, pattern in patterns if re.search(pattern, combined)), "general")

    def adapt(
        self,
        base_response: str | BaseResponse,
        *,
        channel: str,
        request_text: str = "",
        request_type: str | None = None,
        risk_level: str = "low",
        user: str = "REDACTED_f73137d930c3",
        strength: PersonalityStrength = PersonalityStrength.NORMAL,
        previous_styled_text: str = "",
        seed: int = 0,
    ) -> StyledResponse:
        base = base_response if isinstance(base_response, BaseResponse) else BaseResponse.from_text(base_response)
        if channel == "pc_voice" and strength == PersonalityStrength.NORMAL:
            strength = PersonalityStrength.LOW
        kind = request_type or self.infer_request_type(base.text, request_text)
        intent = self.emotion_resolver.resolve(kind, base.text, risk_level)
        voice_style = self.style_selector.resolve(intent.emotion, intent.intensity)
        return self.personality.adapt(
            base,
            ResponseStyleContext(
                user=user,
                channel=channel,
                request_type=kind,
                risk_level=risk_level,
                suggested_emotion=voice_style.emotion,
                suggested_intensity=voice_style.intensity.value,
                personality_strength=strength,
                max_length=320 if channel == "pc_voice" else 500,
                previous_styled_text=previous_styled_text,
            ),
            seed=seed,
        )
