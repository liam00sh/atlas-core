"""Construye una batería pública de 160 frases sin nombres privados."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


CATEGORIES = {
    "conversation": [
        ("Cuéntame algo interesante sobre el océano", "conversation", "", False),
        ("Explícame por qué cambia la hora", "conversation", "", False),
        ("Dime algo divertido", "humor", "", False),
        ("¿Qué tiempo hace hoy?", "weather", "", False),
    ],
    "commands": [
        ("Abre la calculadora", "windows.open", "calculadora", True),
        ("Cierra la calculadora", "windows.close", "calculadora", True),
        ("Reinicia Telegram", "telegram.restart", "Telegram", True),
        ("Cancela la operación", "cancel", "operación", True),
    ],
    "home_assistant": [
        ("Enciende la luz del acuario pequeño", "home.turn_on", "luz del acuario pequeño", True),
        ("Apaga la luz del acuario pequeño", "home.turn_off", "luz del acuario pequeño", True),
        ("¿Está encendida la luz del acuario pequeño?", "home.state", "luz del acuario pequeño", False),
        ("¿Home Assistant está conectado?", "infrastructure.status", "Home Assistant", False),
    ],
    "reminders": [
        ("Acuérdame mañana a las dieciocho treinta revisar Atlas", "reminder.create", "Atlas", True),
        ("Recuérdame hoy a las veinte comprar pan", "reminder.create", "comprar pan", True),
        ("¿Qué recordatorios tengo?", "reminder.list", "", False),
        ("Cancela el recordatorio de revisar Atlas", "reminder.cancel", "Atlas", True),
    ],
    "people": [
        ("Saluda a persona conocida uno", "people.greet", "persona_conocida_1", False),
        ("Presenta a persona conocida dos", "people.introduce", "persona_conocida_2", False),
        ("Persona conocida uno está aquí conmigo", "people.presence", "persona_conocida_1", False),
        ("Despídete de persona conocida dos", "people.farewell", "persona_conocida_2", False),
    ],
    "tools": [
        ("¿Docker está funcionando?", "infrastructure.status", "Docker", False),
        ("¿Telegram está disponible?", "infrastructure.status", "Telegram", False),
        ("¿Ollama está respondiendo?", "infrastructure.status", "Ollama", False),
        ("Comprueba el estado de Atlas", "system.status", "Atlas", False),
    ],
    "confirmation": [
        ("Sí, es correcto", "confirmation.accept", "", False),
        ("No, no era eso", "confirmation.reject", "", False),
        ("Confirma la acción", "confirmation.accept", "", False),
        ("Cancela y déjalo", "confirmation.reject", "", False),
    ],
    "continuity": [
        ("Repite tu respuesta", "repeat.response", "", False),
        ("Repite lo que he dicho", "repeat.user", "", False),
        ("¿Qué has entendido?", "repeat.transcript", "", False),
        ("Explícamelo con más detalle", "continuity.followup", "", False),
    ],
}


def rows() -> list[dict]:
    result = []
    index = 0
    for category, templates in CATEGORIES.items():
        for round_number in range(5):
            for text, intent, entity, safe_action in templates:
                index += 1
                suffix = "" if round_number == 0 else (" por favor" if round_number % 2 else " ahora")
                result.append({
                    "id": index,
                    "category": category,
                    "expected_text": text + suffix,
                    "expected_intent": intent,
                    "expected_entity": entity,
                    "command_expected": bool(safe_action),
                    "safe_action_expected": bool(safe_action),
                    "audio_file": "",
                    "raw_transcript": "",
                    "normalized_transcript": "",
                    "observed_intent": "",
                    "observed_entity": "",
                    "command_observed": "",
                    "safe_action_observed": "",
                })
    assert len(result) == 160
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = rows()
    if args.output.suffix.casefold() == ".json":
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
