"""Analiza un diagnóstico físico ya capturado sin contactar Home Assistant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def analyze(report: dict) -> dict:
    actions = []
    all_consistent = bool(report.get("actions_executed"))
    for service, expected in (("turn_on", "on"), ("turn_off", "off")):
        run = report.get(service) or {}
        samples = run.get("api_samples") or []
        matching = [sample for sample in samples if sample.get("state") == expected]
        first_match = min((float(sample["delay_seconds"]) for sample in matching), default=None)
        stable_after_match = bool(matching) and all(
            sample.get("state") == expected
            for sample in samples
            if float(sample["delay_seconds"]) >= float(first_match)
        )
        physical = run.get("physical_observation") == expected
        ui = run.get("home_assistant_ui_observation") == expected
        consistent = physical and ui and stable_after_match
        all_consistent = all_consistent and consistent
        actions.append({
            "service": service,
            "expected_state": expected,
            "service_response_state": (run.get("service_response") or {}).get("state"),
            "service_response_was_stale": (run.get("service_response") or {}).get("state") != expected,
            "first_confirmed_api_seconds": first_match,
            "api_stable_after_confirmation": stable_after_match,
            "physical_observation": run.get("physical_observation"),
            "home_assistant_ui_observation": run.get("home_assistant_ui_observation"),
            "last_changed": matching[0].get("last_changed") if matching else None,
            "last_updated": matching[0].get("last_updated") if matching else None,
            "consistent": consistent,
        })
    return {
        "schema_version": 1,
        "status": "NOT_REPRODUCED" if all_consistent else "STILL_OPEN",
        "entity_id": (report.get("alias_resolution") or {}).get("entity_id"),
        "configured_constant_matches": report.get("configured_constant_matches"),
        "actions": actions,
        "conclusion": (
            "Las órdenes on/off coincidieron en dispositivo físico, interfaz y API. El fallo histórico "
            "físico ON/API OFF no se reprodujo. La respuesta del servicio y las lecturas hasta 0,25 s "
            "fueron obsoletas; la API confirmó el estado a 0,5 s. Esto explica una lectura prematura, "
            "pero no demuestra la causa exacta del incidente histórico."
            if all_consistent else
            "Al menos una acción no quedó confirmada de forma consistente en dispositivo físico, interfaz y API."
        ),
        "historical_bug_erased": False,
    }


def markdown(result: dict) -> str:
    lines = [
        "# Conclusión del diagnóstico Home Assistant", "",
        f"Estado: **{result['status']}**", "",
        f"Entidad exacta: `{result['entity_id']}`", "",
        result["conclusion"], "",
        "| Acción | Respuesta inmediata | Confirmación API | Físico | UI |", "|---|---|---:|---|---|",
    ]
    for action in result["actions"]:
        lines.append(
            f"| {action['service']} | {action['service_response_state']} | "
            f"{action['first_confirmed_api_seconds']} s | {action['physical_observation']} | "
            f"{action['home_assistant_ui_observation']} |"
        )
    lines += ["", "El incidente anterior se conserva como antecedente; este resultado no lo reescribe como inexistente.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    source_hash_before = args.input.read_bytes()
    result = analyze(json.loads(source_hash_before.decode("utf-8-sig")))
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(result), encoding="utf-8")
    if args.input.read_bytes() != source_hash_before:
        raise RuntimeError("El diagnóstico fuente cambió durante el análisis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
