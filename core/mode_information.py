"""Respuestas deterministas sobre modos de Atlas."""
from __future__ import annotations

MODE_SUMMARIES = {
    "Clásico": "tono cercano, natural y equilibrado.",
    "Divertido": "más bromista, festivo y espontáneo.",
    "Trabajo": "directo, técnico, ordenado y centrado en la tarea.",
    "Emotivo": "más cálido, cuidadoso y atento al estado emocional.",
}

MODE_ALIASES = {
    "normal": "Clásico",
    "clasico": "Clásico",
    "clásico": "Clásico",
    "divertido": "Divertido",
    "bromista": "Divertido",
    "fiesta": "Divertido",
    "trabajo": "Trabajo",
    "profesional": "Trabajo",
    "tecnico": "Trabajo",
    "técnico": "Trabajo",
    "emotivo": "Emotivo",
    "emocional": "Emotivo",
}

def render_modes() -> str:
    lines = ["Atlas dispone de cuatro modos:"]
    for name, description in MODE_SUMMARIES.items():
        lines.append(f"• {name}: {description}")
    return "\n".join(lines)
