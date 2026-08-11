"""Compara Kokoro por proceso y Kokoro persistente con texto no sensible."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telegram_interface.voice_delivery import TelegramVoiceRenderer
from voice.preferences.voice_preferences import VoicePreferences
from voice.providers.kokoro_provider import KokoroProvider
from voice.service import VoiceService


@contextmanager
def persistent_mode(enabled: bool):
    previous = os.environ.get("ATLAS_KOKORO_PERSISTENT")
    os.environ["ATLAS_KOKORO_PERSISTENT"] = "true" if enabled else "false"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("ATLAS_KOKORO_PERSISTENT", None)
        else:
            os.environ["ATLAS_KOKORO_PERSISTENT"] = previous


def measure(mode: str, persistent: bool, root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with persistent_mode(persistent):
        provider = KokoroProvider(timeout_seconds=180)
        service = VoiceService(provider=provider, output_dir=root / mode / "wav")
        renderer = TelegramVoiceRenderer(
            voice_service=service,
            preference_resolver=lambda _user: VoicePreferences(daxter_voice_id="daxter_alex"),
            personality_resolver=lambda _user: "daxter",
            output_dir=root / mode / "ogg",
        )
        try:
            for iteration in (1, 2):
                result = renderer.render("REDACTED_0f38c2ded26fnando y atento, Alex. ¿Cómo estás tú?", user_id="benchmark")
                records.append({
                    "mode": mode,
                    "iteration": iteration,
                    "success": result.success,
                    "error": result.error,
                    "timings_ms": result.timings_ms,
                })
                renderer.cleanup(result)
        finally:
            provider.close()
    return records


def run(output: Path) -> Path:
    with TemporaryDirectory(prefix="atlas-tts-benchmark-") as temporary:
        root = Path(temporary)
        records = [
            *measure("one_shot_before", False, root),
            *measure("persistent_after", True, root),
        ]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "text_contains_personal_data": False,
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_output.replace(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "evidence" / "tts_latency_benchmark_2026-08-09.json",
    )
    args = parser.parse_args()
    print(run(args.output))


if __name__ == "__main__":
    main()
