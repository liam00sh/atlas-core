"""Smoke benchmark secuencial de los tres modelos locales de Atlas."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.benchmark import BenchmarkRecord, BenchmarkRecorder
from ai.models.roles import ModelRole, ModelRoleRegistry
from ai.providers.ollama_provider import OllamaProvider


CASES = {
    ModelRole.FAST: (
        "Responde en español con una única frase corta sobre un acuario tranquilo. "
        "No saludes ni inventes experiencias propias."
    ),
    ModelRole.REASONING: (
        "Turno anterior del usuario: Me gusta más el invierno que el verano. "
        "Pregunta actual: ¿Por qué crees que te acabo de decir eso? "
        "Razona sobre la intención comunicativa con prudencia, sin fingir recuerdos."
    ),
    ModelRole.DEEP: (
        "Analiza esta contradicción técnica sin inventar datos: una fuente verificada "
        "dice que el servicio está detenido y una nota no verificada dice que está "
        "activo. Explica qué fuente gobierna la verdad y qué comprobarías después."
    ),
}


def run(output: Path) -> Path:
    registry = ModelRoleRegistry()
    recorder = BenchmarkRecorder()
    ollama = shutil.which("ollama")
    for role in (ModelRole.FAST, ModelRole.REASONING, ModelRole.DEEP):
        definition = registry.resolve(role)
        provider = OllamaProvider(str(definition.model), timeout=360)
        started = perf_counter()
        answer = ""
        error = ""
        try:
            answer = provider.generate(CASES[role])
        except (RuntimeError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        elapsed = perf_counter() - started
        words = len(answer.split())
        success = bool(answer) and (role is not ModelRole.FAST or words <= 40)
        recorder.add(BenchmarkRecord(
            input=CASES[role],
            mode=role.value,
            route=role.value,
            model=str(definition.model),
            fallback=False,
            latency_seconds=elapsed,
            success=success,
            selection_reason="live_role_smoke",
            expected="respuesta local no vacía" + (" y breve" if role is ModelRole.FAST else ""),
            obtained=answer or error,
        ))
        if ollama:
            subprocess.run(
                [ollama, "stop", str(definition.model)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    return recorder.write(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "evidence" / "live_model_benchmark_2026-08-09.json",
    )
    args = parser.parse_args()
    print(run(args.output))


if __name__ == "__main__":
    main()
