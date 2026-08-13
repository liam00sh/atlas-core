"""Diagnóstico físico/UI/API de una entidad; no cambia el router productivo."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.home_assistant_client import HomeAssistantHttpClient
from automation.home_assistant_factory import create_home_assistant_client, load_home_assistant_settings
from automation.home_intent_resolver import HomeIntentResolver, REAL_HOME_ENTITIES


DELAYS = (0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0)
DEFAULT_ALIAS = "luz del acuario pequeño"


def compact_state(state) -> dict:
    attrs = dict(state.attributes)
    return {
        "entity_id": state.entity_id, "domain": state.entity_id.split(".", 1)[0],
        "state": state.state, "friendly_name": attrs.get("friendly_name"),
        "platform": attrs.get("platform"), "integration": attrs.get("integration"),
        "supported_features": attrs.get("supported_features"), "attributes": attrs,
        "last_changed": state.last_changed, "last_updated": state.last_updated,
    }


def resolve_alias(alias: str) -> dict:
    intent = HomeIntentResolver().resolve(f"Enciende {alias}")
    if intent is None:
        raise ValueError(f"Atlas no resolvió el alias: {alias}")
    return {"alias": alias, "action_id": intent.action_id, "entity_id": intent.parameters["entity_id"]}


def sample_after_service(client, entity_id: str, service: str, *, sleep=time.sleep) -> dict:
    domain = entity_id.split(".", 1)[0]
    started = time.perf_counter()
    service_state = client.call_service(domain, service, entity_id=entity_id)
    samples = []
    previous = 0.0
    for delay in DELAYS:
        sleep(max(0.0, delay - previous))
        previous = delay
        samples.append({"delay_seconds": delay, **compact_state(client.get_state(entity_id))})
    return {
        "service": service, "service_response": compact_state(service_state),
        "elapsed_seconds": round(time.perf_counter() - started, 4), "api_samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara el estado físico, la UI y la API de Home Assistant.")
    parser.add_argument("--env", type=Path, required=True)
    parser.add_argument("--alias", default=DEFAULT_ALIAS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-actions", action="store_true", help="Envía turn_on y turn_off incluso si el estado ya coincide.")
    args = parser.parse_args()
    settings = load_home_assistant_settings(env_file=args.env)
    if settings.mode != "real":
        parser.error("El diagnóstico físico requiere HOME_ASSISTANT_MODE=real.")
    client = create_home_assistant_client(settings)
    if not isinstance(client, HomeAssistantHttpClient):
        parser.error("El diagnóstico requiere el cliente HTTP real.")
    resolved = resolve_alias(args.alias)
    entity_id = resolved["entity_id"]
    all_states = client.list_states()
    related = [
        compact_state(state) for state in all_states
        if any(term in (state.entity_id + " " + str(state.attributes.get("friendly_name", ""))).casefold() for term in ("acuario", "pequeñ", "luz"))
    ]
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "alias_resolution": resolved, "configured_constant_matches": entity_id == REAL_HOME_ENTITIES["luz_acuario_pequeno"],
        "initial_state": compact_state(client.get_state(entity_id)), "related_entities": related,
        "actions_executed": False, "turn_on": None, "turn_off": None,
        "rest_api_limit": "platform/integration quedan nulos si Home Assistant no los publica como atributos de estado",
        "hypothesis": None,
    }
    if args.run_actions:
        confirmation = input(f"Se enviarán turn_on y turn_off a {entity_id}. Escribe DIAGNOSTICAR para continuar: ").strip()
        if confirmation != "DIAGNOSTICAR":
            print("Cancelado sin enviar servicios.")
            return 3
        report["actions_executed"] = True
        for service, expected in (("turn_on", "encendida"), ("turn_off", "apagada")):
            print(f"Enviando {service}. Observa la luz y la interfaz de Home Assistant.")
            run = sample_after_service(client, entity_id, service)
            input(f"Pulsa Enter cuando hayas comprobado físicamente que la luz está {expected} (o que no cambió)…")
            run["physical_observation"] = input("Estado físico [on/off/no_cambio/desconocido]: ").strip().casefold()
            run["home_assistant_ui_observation"] = input("Estado visible en la UI [on/off/unavailable/desconocido]: ").strip().casefold()
            run["observation_notes"] = input("Notas breves: ").strip()
            report[service] = run
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = [
        "# Diagnóstico Home Assistant", "", f"Alias: `{args.alias}`", f"Entidad: `{entity_id}`",
        f"Acciones ejecutadas: {'sí' if report['actions_executed'] else 'no'}", "",
        "No se concluye una causa sin comparar observación física, UI y API.",
        "Hipótesis abiertas: entidad/alias incorrectos, estado stale, retraso Tuya, optimistic state, polling, switch frente a light, entidad duplicada, integración o disponibilidad.",
    ]
    args.output.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(f"Informe: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
