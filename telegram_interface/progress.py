"""Mensajes de progreso y tiempos de respuesta para Telegram."""
from __future__ import annotations

import random
import re
import unicodedata


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


def progress_delay_for(text: str, default: float = 4.0) -> float:
    """Muestra progreso solo si una operación sigue activa tras cuatro segundos.

    Saludos, conversación social muy breve y consultas deterministas no deben
    mostrar un aviso de espera aunque el equipo esté momentáneamente ocupado.
    """
    normalized = _plain(text)
    trivial = {
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
        "como estas", "que tal", "gracias", "vale", "ok", "adios",
    }
    if normalized in trivial:
        return -1.0
    return 4.0


def build_progress_message(text: str, personality: str) -> str:
    personality = str(personality or "Daxter").casefold()
    operation = classify_operation(text)
    daxter = {
        "internet": (
            "Me pongo el sombrero de explorador web. Un segundo 🌍",
            "Déjame rebuscar por Internet; vuelvo con algo verificable 🔎",
            "Voy a rastrear la red sin caer en la inventicia. Dame un momento 🧭",
        ),
        "drive_index": (
            "Estoy poniendo el índice de Drive en formación. Puede tardar un poco 🗂️",
            "Revisando Drive documento por documento. Esto lleva unos segundos 📚",
        ),
        "translation": (
            "Estoy afinando la traducción; que no se escape ningún matiz 🗣️",
        ),
        "generic": (
            "Dame un momento, estoy conectando los cables mentales ⚡",
            "Estoy ordenando la información para responderte bien 🧠",
        ),
    }
    coco = {
        "internet": (
            "Dame un momento, voy a buscar una fuente fiable 🔎",
            "Estoy navegando para comprobarlo bien 🌍",
        ),
        "drive_index": (
            "Estoy revisando y actualizando el índice de Drive 📚",
            "Un momento, estoy ordenando los documentos de Drive 🗂️",
        ),
        "translation": (
            "Estoy cuidando la traducción para que suene natural ✨",
        ),
        "generic": (
            "Un momento, estoy preparando una respuesta clara ✨",
            "Estoy revisándolo con calma para responderte bien 🙂",
        ),
    }
    catalog = coco if personality == "coco" else daxter
    return random.choice(catalog[operation])


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
