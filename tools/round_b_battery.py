"""Baterías y configuraciones reproducibles de la Ronda B de Daxter."""

from __future__ import annotations

import re

from tools.voice_lab_battery import BATTERY as ORIGINAL_BATTERY


ORIGINAL_EMOTIONS = {
    "01_neutral": "neutral", "02_sonriente": "sonriente", "03_travieso": "travieso",
    "04_sorprendido": "sorprendido", "05_emocionado": "emocionado", "06_asustado": "asustado",
    "07_enfadado": "enfadado", "08_curioso": "curioso", "09_confiado": "confiado",
    "10_determinado": "determinado", "11_jugueton": "travieso", "12_numeros_nombres": "neutral",
    "13_larga": "neutral",
}

CORRECTED_BATTERY = (
    ("01_neutral", "Atlas está listo. Todo funciona con normalidad.", "neutral"),
    ("02_sonriente", "Hola Alex. Me alegra verte por aquí.", "sonriente"),
    ("03_travieso", "Je, je. Seguro que este botón no hace nada peligroso.", "travieso"),
    ("04_sorprendido", "¡Qué! ¿Eso sí que no me lo esperaba?", "sorprendido"),
    ("05_emocionado", "¡Vamos, Jak! ¡Esta aventura acaba de empezar!", "emocionado"),
    ("06_asustado", "Espera, espera. ¿Has oído ese ruido detrás de nosotros?", "asustado"),
    ("07_enfadado", "¡Eh! ¡Devuélveme eso ahora mismo!", "enfadado"),
    ("08_curioso", "Oye Atlas ¿cómo funciona exactamente ese cacharro?", "curioso"),
    ("09_confiado", "Tranquilo. Lo tengo todo bajo control.", "confiado"),
    ("10_determinado", "No nos rendiremos. Encontraremos una salida.", "determinado"),
    ("11_jugueton", "A que no me pillas, Jak. ¡Vamos, inténtalo!", "travieso"),
    ("12_numeros_nombres", "Alex y Vega probarán Atlas el nueve de agosto de dos mil veintiséis, a las dieciocho cuarenta y cinco, con mil trescientas muestras.", "neutral"),
    ("13_larga", "Atlas procesa la petición localmente y conserva los permisos del núcleo. Si la voz principal falla, utiliza una alternativa española sin repetir acciones ni ocultar el error.", "neutral"),
    ("14_atlas", "Atlas está listo.", "neutral"),
    ("15_hola", "Hola, Alex.", "sonriente"),
    ("16_jak_espera", "Jak, espera.", "determinado"),
    ("17_espera", "Espera, espera.", "asustado"),
    ("18_oye_atlas", "Oye Atlas, tengo una idea.", "curioso"),
    ("19_aqui", "Aquí tenemos todo preparado.", "confiado"),
    ("20_tecnica", "Atlas ejecuta Home Assistant localmente y envía avisos por Telegram sin revelar datos privados.", "neutral"),
    ("21_fecha_numeros", "La prueba número trece será el nueve de agosto de dos mil veintiséis a las dieciocho cuarenta y cinco.", "neutral"),
)

CANDIDATES = {
    "B0": {
        "label": "baseline_Ronda_A",
        "reference_strategy": "jak2_diverse",
        "normalize_pronunciation": False,
        "cfg_weight": 0.35,
        "temperature": 0.8,
        "repetition_penalty": 2.0,
        "min_p": 0.05,
        "top_p": 1.0,
        "purpose": "Baseline exacto de Ronda A para comparación histórica.",
    },
    "B1": {
        "label": "normalizacion_inferencia",
        "reference_strategy": "jak2_diverse",
        "normalize_pronunciation": True,
        "cfg_weight": 0.35,
        "temperature": 0.8,
        "repetition_penalty": 2.0,
        "min_p": 0.05,
        "top_p": 1.0,
        "purpose": "Aísla el efecto de pronunciación y números sin cambiar el conditioning.",
    },
    "B2": {
        "label": "conditioning_es_es_nombres",
        "reference_strategy": "spain_names",
        "normalize_pronunciation": True,
        "cfg_weight": 0.30,
        "temperature": 0.7,
        "repetition_penalty": 2.0,
        "min_p": 0.05,
        "top_p": 1.0,
        "purpose": "Prioriza referencias españolas con Jak, espera y hola; pacing más deliberado.",
    },
    "B3": {
        "label": "conditioning_emocional_dinamico",
        "reference_strategy": "emotion_matched",
        "normalize_pronunciation": True,
        "cfg_weight": 0.30,
        "temperature": 0.7,
        "repetition_penalty": 2.0,
        "min_p": 0.05,
        "top_p": 1.0,
        "purpose": "Usa una referencia de Daxter emparejada por emoción; identidad debe validarse a oído.",
    },
}

PRONUNCIATION_RULES = (
    (r"\bJak\b", "Yak"),
    (r"\bAtlas\b", "Átlas"),
    (r"\bDaxter\b", "Dákster"),
    (r"\bHome Assistant\b", "Joum Asístent"),
    (r"\bTelegram\b", "Télegram"),
)


def normalize_for_inference(text: str) -> str:
    """Aplica sólo a síntesis; nunca se escribe sobre el metadata humano."""
    for pattern, replacement in PRONUNCIATION_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    replacements = {
        "el 9 de agosto de 2026": "el nueve de agosto de dos mil veintiséis",
        "a las 18:45": "a las dieciocho cuarenta y cinco",
        "1.300 muestras": "mil trescientas muestras",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def battery(name: str) -> tuple[tuple[str, str, str], ...]:
    if name == "original":
        return tuple((case_id, text, ORIGINAL_EMOTIONS[case_id]) for case_id, text in ORIGINAL_BATTERY)
    if name == "corrected":
        return CORRECTED_BATTERY
    raise ValueError(f"Batería desconocida: {name}")


def exaggeration(case_id: str, emotion: str, candidate: str) -> float:
    if emotion in {"neutral", "confiado"} or case_id in {"12_numeros_nombres", "13_larga", "20_tecnica", "21_fecha_numeros"}:
        return 0.45 if candidate != "B3" else 0.50
    return 0.65 if candidate != "B3" else 0.70
