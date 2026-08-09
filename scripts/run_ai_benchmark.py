"""Genera una comparación reproducible del router sin invocar Internet."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.benchmark import BenchmarkRecord, BenchmarkRecorder
from ai.models.roles import ModelRoleRegistry
from ai.routing.router import AIRouter, RoutingRequest


CASES = (
    ("Hola", {}, "fast"),
    ("¿Y ella dónde estaba antes?", {"context_messages": 4, "temporal_reasoning": True}, "reasoning"),
    ("¿Qué te dije sobre mi proyecto?", {"context_messages": 2, "memory_required": True}, "reasoning"),
    ("Analiza estas fuentes contradictorias", {"retrieved_items": 12, "has_contradictions": True}, "deep"),
)


def run(output: Path) -> Path:
    registry = ModelRoleRegistry()
    recorder = BenchmarkRecorder()
    for mode in ("auto", "fast", "reasoning", "deep"):
        router = AIRouter(override=mode)
        for message, arguments, expected_auto in CASES:
            started = perf_counter()
            decision = router.route(RoutingRequest(message, **arguments))
            elapsed = perf_counter() - started
            expected = expected_auto if mode == "auto" else mode
            definition = registry.resolve(decision.role)
            recorder.add(BenchmarkRecord(
                input=message,
                mode=mode,
                route=decision.role.value,
                model=str(definition.model),
                fallback=False,
                latency_seconds=elapsed,
                success=decision.role.value == expected,
                selection_reason=decision.reason,
                memory_used=bool(arguments.get("memory_required")),
                tools_used=(),
                web_search=False,
                expected=expected,
                obtained=decision.role.value,
            ))
    return recorder.write(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "evidence" / "atlas_ai_benchmark_2026-08-09.json",
    )
    args = parser.parse_args()
    print(run(args.output))


if __name__ == "__main__":
    main()
