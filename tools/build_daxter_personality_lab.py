"""Construye 40 situaciones offline para evaluar el adaptador de personalidad."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path

from conversation.daxter_personality import PersonalityAdapter, PersonalityStrength, ResponseStyleContext


CASE_BLUEPRINTS = (
    ("saludo", "greeting", "Hola, REDACTED_2c7b6821719d. Estoy listo.", "sonriente", "media", "normal"),
    ("saludo_noche", "greeting", "Buenas noches. El sistema está disponible.", "cansado", "baja", "normal"),
    ("pregunta_normal", "general", "Madrid es la capital de España.", "neutral", "media", "normal"),
    ("pregunta_normal_2", "general", "La copia ocupa 2,4 gigabytes.", "neutral", "media", "low"),
    ("curiosidad", "casual", "Los pulpos tienen tres corazones.", "curioso", "media", "normal"),
    ("curiosidad_2", "casual", "Ese sensor mide temperatura y humedad.", "curioso", "media", "high"),
    ("broma", "casual", "El archivo estaba en la carpeta que ya habíamos revisado.", "travieso", "media", "high"),
    ("broma_2", "casual", "El error desapareció al reiniciar el servicio.", "picaro", "media", "normal"),
    ("error", "error", "No pude guardar el archivo porque la unidad está llena.", "pensativo", "media", "normal"),
    ("error_2", "error", "La cámara no respondió y no se ejecutó ninguna acción.", "sorprendido", "media", "normal"),
    ("error_3", "error", "La solicitud caducó después de treinta segundos.", "cansado", "baja", "low"),
    ("home_assistant", "success", "La luz del salón está encendida al 40 %.", "confiado", "media", "normal"),
    ("home_assistant_2", "success", "El termostato se ha ajustado a 21 grados.", "confiado", "media", "normal"),
    ("home_assistant_fallo", "error", "Home Assistant no confirmó la acción; la luz no se modificó.", "pensativo", "media", "low"),
    ("accion_completada", "success", "La copia de seguridad terminó correctamente.", "emocionado", "media", "high"),
    ("accion_completada_2", "success", "El mensaje se entregó a REDACTED_bc04a68d9192.", "sonriente", "media", "normal"),
    ("accion_fallida", "error", "El mensaje no se envió porque Telegram no está disponible.", "pensativo", "media", "normal"),
    ("accion_fallida_2", "error", "No abrí la puerta porque falta confirmación.", "determinado", "media", "low"),
    ("aviso", "general", "Quedan diez minutos para la reunión.", "neutral", "media", "normal"),
    ("aviso_2", "general", "La batería del portátil está al 12 %.", "sorprendido", "media", "normal"),
    ("tecnica", "technical", "El proceso usa 612 megabytes de memoria y no presenta errores.", "neutral", "media", "normal"),
    ("tecnica_2", "technical", "La rama local y la remota apuntan al mismo commit.", "neutral", "media", "normal"),
    ("tecnica_3", "technical", "La latencia media es de 83 milisegundos.", "neutral", "media", "low"),
    ("privacidad", "privacy", "No puedo mostrar la conversación privada de otro usuario.", "neutral", "baja", "normal"),
    ("privacidad_2", "privacy", "Necesito tu autorización antes de consultar ese documento privado.", "neutral", "baja", "high"),
    ("seguridad", "security", "La operación está bloqueada porque el archivo no supera la validación.", "neutral", "baja", "normal"),
    ("seguridad_2", "security", "No ejecutaré el comando sin una confirmación explícita.", "neutral", "baja", "high"),
    ("casual", "casual", "Hoy no hay tareas pendientes en el calendario.", "sonriente", "media", "normal"),
    ("casual_2", "casual", "El fin de semana estará libre después de las seis.", "confiado", "media", "high"),
    ("emocional", "casual", "Entiendo que haya sido un día difícil. Podemos ir paso a paso.", "pensativo", "baja", "low"),
    ("emocional_2", "casual", "Has terminado una tarea complicada y el resultado es correcto.", "emocionado", "media", "normal"),
    ("conduccion", "driving", "Gira a la derecha dentro de cien metros.", "neutral", "baja", "high"),
    ("conduccion_2", "driving", "Hay retención a dos kilómetros; mantén el carril actual.", "neutral", "baja", "normal"),
    ("emergencia", "emergency", "Llama al 112 y aléjate del humo inmediatamente.", "neutral", "baja", "high"),
    ("emergencia_2", "emergency", "No toques el cable y corta la corriente desde un lugar seguro.", "neutral", "baja", "normal"),
    ("determinacion", "general", "Quedan tres pruebas; continuaremos hasta completarlas.", "determinado", "alta", "normal"),
    ("miedo_controlado", "general", "El sensor detectó movimiento, pero la alarma sigue desactivada.", "asustado", "media", "normal"),
    ("sorpresa", "casual", "La actualización terminó antes de lo previsto.", "sorprendido", "media", "normal"),
    ("cansancio", "general", "La tarea larga terminó y no quedan procesos activos.", "cansado", "baja", "normal"),
    ("risa_breve", "casual", "El fallo era un espacio al final del nombre del archivo.", "risa", "media", "high"),
)


REVIEW_FIELDS = (
    "case_id", "category", "respuesta_base", "respuesta_daxter", "emocion", "intensidad",
    "personality_strength", "parece_daxter_1_5", "naturalidad_1_5", "humor_adecuado_1_5",
    "intensidad_adecuada_1_5", "conserva_informacion_1_5", "demasiado_daxter_si_no",
    "demasiado_serio_si_no", "notas",
)


def build_cases(seed: int = 20260811) -> list[dict]:
    adapter = PersonalityAdapter()
    cases = []
    for index, (category, request_type, base, emotion, intensity, strength) in enumerate(CASE_BLUEPRINTS, 1):
        context = ResponseStyleContext(
            request_type=request_type,
            risk_level="critical" if request_type == "emergency" else "high" if request_type in {"privacy", "security"} else "low",
            suggested_emotion=emotion,
            suggested_intensity=intensity,
            personality_strength=PersonalityStrength(strength),
            night_mode=category == "saludo_noche",
        )
        result = adapter.adapt(base, context, seed=seed + index)
        cases.append({
            "case_id": f"P{index:03d}", "category": category, "request_type": request_type,
            "respuesta_base": base, "respuesta_daxter": result.styled_text,
            "emocion": result.emotion, "intensidad": result.intensity,
            "personality_strength_requested": strength,
            "personality_strength": result.personality_strength_used.value,
            "reason": result.reason,
        })
    return cases


def player_html(cases: list[dict]) -> str:
    cards = []
    for case in cases:
        cards.append(
            f'<article data-category="{html.escape(case["request_type"])}"><h2>{case["case_id"]} · {html.escape(case["category"])}</h2>'
            f'<p><strong>Base:</strong> {html.escape(case["respuesta_base"])}</p>'
            f'<p><strong>Daxter:</strong> {html.escape(case["respuesta_daxter"])}</p>'
            f'<p class="meta">{html.escape(case["emocion"])} · {html.escape(case["intensidad"])} · {html.escape(case["personality_strength"])}</p></article>'
        )
    return """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laboratorio de personalidad de Daxter</title><style>
body{font-family:system-ui,sans-serif;max-width:1050px;margin:auto;padding:24px;background:#10131a;color:#f5f6fa}article{background:#1b2130;border:1px solid #35405a;border-radius:10px;padding:16px;margin:14px 0}.meta{color:#ffb45b}p{line-height:1.5}
</style></head><body><h1>Evaluación offline de personalidad</h1><p>Compara el contenido base con la forma Daxter. Verifica sobre todo que no cambie ningún hecho.</p>""" + "".join(cards) + "</body></html>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260811)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases(args.seed)
    (args.output_dir / "PERSONALITY_CASES.json").write_text(json.dumps({"seed": args.seed, "cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "PERSONALITY_REVIEW.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for case in cases:
            writer.writerow({
                "case_id": case["case_id"], "category": case["category"],
                "respuesta_base": case["respuesta_base"], "respuesta_daxter": case["respuesta_daxter"],
                "emocion": case["emocion"], "intensidad": case["intensidad"],
                "personality_strength": case["personality_strength"],
            })
    (args.output_dir / "PERSONALITY_REVIEW.html").write_text(player_html(cases), encoding="utf-8")
    print(json.dumps({"cases": len(cases), "output": str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
