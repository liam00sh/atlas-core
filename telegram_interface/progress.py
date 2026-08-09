"""Mensajes de progreso y tiempos de respuesta para Telegram."""
from __future__ import annotations

import random
import re
import unicodedata
from conversation.event_messages import ContextualMessageGenerator

_MESSAGE_GENERATOR = ContextualMessageGenerator()


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9ñ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def classify_operation(text: str) -> str:
    normalized = _plain(text)
    if any(marker in normalized for marker in ("busca en internet", "consulta en internet", "busca online", "investiga en la web")):
        return "internet"
    if any(marker in normalized for marker in ("actualiza el indice", "actualizar indice", "reindexa", "indexa drive", "indice de drive")):
        return "drive_index"
    if any(marker in normalized for marker in ("traduce", "traducir", "como se dice")):
        return "translation"
    return "generic"


def classify_progress(text: str) -> str:
    """Alias compatible para pruebas e integraciones anteriores."""
    return classify_operation(text)


def progress_delay_for(text: str, default: float = 4.5) -> float:
    """Calcula cuándo mostrar progreso según el tipo de petición."""

    normalized = _plain(text)

    social_exact = {
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
        "como estas", "que tal", "gracias", "muchas gracias", "vale", "ok",
        "adios", "hasta luego",
    }
    if normalized in social_exact:
        return -1.0

    # Nunca se anuncia espera antes de que exista latencia perceptible real.
    # Las órdenes directas suelen terminar antes de este umbral y no muestran nada.
    return max(4.5, float(default))


def build_progress_message(text: str, personality: str) -> str:
    operation = classify_operation(text)
    situation = {
        "internet": "comprobando fuentes web autorizadas",
        "drive_index": "revisando el índice de Drive",
        "translation": "cuidando la traducción",
        "generic": "ordenando la respuesta",
    }[operation]
    return _MESSAGE_GENERATOR.generate(
        "progress",
        user="usuario",
        assistant=str(personality or "Daxter").title(),
        channel="telegram",
        situation=situation,
    )


def append_response_time(text: str, elapsed_seconds: float, personality: str) -> str:
    """Añade tiempo solo cuando la operación ha sido perceptiblemente lenta."""
    if elapsed_seconds < 2.5:
        return text
    shown = f"{elapsed_seconds:.1f}".replace(".", ",")
    if str(personality or "").casefold() == "coco":
        footer = f"⏱️ Listo en {shown} s."
    else:
        footer = f"⏱️ Misión resuelta en {shown} s."
    return f"{text.rstrip()}\n\n{footer}"
