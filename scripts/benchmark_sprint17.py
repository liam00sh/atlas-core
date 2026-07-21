"""Benchmark reproducible y no destructivo del Sprint 17."""

from __future__ import annotations

import argparse
import builtins
import cProfile
import io
import json
import os
import pstats
import sys
import time
import tracemalloc
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def measure(callable_):
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    value = callable_()
    return value, {
        "wall_ms": round((time.perf_counter() - started_wall) * 1000, 3),
        "cpu_ms": round((time.process_time() - started_cpu) * 1000, 3),
    }


def main(output: Path) -> None:
    from core.atlas import Atlas

    counters = {"json_reads": 0, "json_writes": 0}
    provider_metrics = {"availability_calls": 0, "generate_calls": 0, "prompt_chars": 0}

    class CountingLocalProvider:
        def is_available(self):
            provider_metrics["availability_calls"] += 1
            return True

        def generate(self, prompt):
            provider_metrics["generate_calls"] += 1
            provider_metrics["prompt_chars"] = len(prompt)
            return "Respuesta local de benchmark."
    original_open = builtins.open

    def counted_open(file, mode="r", *args, **kwargs):
        path = str(file).casefold()
        if path.endswith((".json", ".jsonl")):
            if "r" in mode:
                counters["json_reads"] += 1
            if any(flag in mode for flag in ("w", "a", "+")):
                counters["json_writes"] += 1
        return original_open(file, mode, *args, **kwargs)

    profile = cProfile.Profile()
    tracemalloc.start()
    with patch("builtins.open", counted_open):
        profile.enable()
        atlas, startup = measure(lambda: Atlas(ai_provider=None))
        profile.disable()
        current, peak = tracemalloc.get_traced_memory()

        user_id = atlas.get_user()
        profile_data = atlas.users.get_profile(user_id)

        def silent_process(text: str):
            with redirect_stdout(io.StringIO()):
                return atlas.process(text)

        _, simple_first = measure(lambda: silent_process("hola"))
        _, simple_second = measure(lambda: silent_process("hola"))
        _, memory_first = measure(
            lambda: atlas.memory_retriever.find(
                "coche", owner=user_id, viewer=user_id,
                viewer_profile=profile_data, limit=5,
            )
        )
        _, memory_second = measure(
            lambda: atlas.memory_retriever.find(
                "coche", owner=user_id, viewer=user_id,
                viewer_profile=profile_data, limit=5,
            )
        )
        _, knowledge_first = measure(
            lambda: atlas.knowledge_retriever.retrieve("arquitectura Atlas", user_id=user_id)
        )
        _, knowledge_second = measure(
            lambda: atlas.knowledge_retriever.retrieve("arquitectura Atlas", user_id=user_id)
        )
        original_provider = atlas.knowledge_service.provider
        atlas.knowledge_service.provider = CountingLocalProvider()
        _, local_ai = measure(
            lambda: atlas.knowledge_service.answer(
                "Resume la arquitectura de Atlas",
                user_id=user_id,
            )
        )
        atlas.knowledge_service.provider = original_provider
        _, document_first = measure(
            lambda: atlas.google_drive_document_index.search_chunks("OAuth", limit=5)
        )
        _, document_second = measure(
            lambda: atlas.google_drive_document_index.search_chunks("OAuth", limit=5)
        )
        _, tool_first = measure(lambda: atlas.execute_framework_tool("system.status.read"))
        _, tool_second = measure(lambda: atlas.execute_framework_tool("system.status.read"))

    tracemalloc.stop()
    stats_stream = io.StringIO()
    pstats.Stats(profile, stream=stats_stream).strip_dirs().sort_stats("cumulative").print_stats(25)
    result = {
        "python": os.sys.version,
        "startup": startup,
        "memory_bytes": {"current": current, "peak": peak},
        "io": counters,
        "queries": {
            "simple_first": simple_first, "simple_second": simple_second,
            "memory_first": memory_first, "memory_second": memory_second,
            "knowledge_first": knowledge_first, "knowledge_second": knowledge_second,
            "local_ai_pipeline": local_ai,
            "document_first": document_first, "document_second": document_second,
            "tool_first": tool_first, "tool_second": tool_second,
        },
        "local_provider_metrics": provider_metrics,
        "drive_calls": 0,
        "profile_top": stats_stream.getvalue(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    main(arguments.output)
