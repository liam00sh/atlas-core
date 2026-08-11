"""Generate a private before/after pronunciation and endpoint battery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
import wave
import math

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.models import SynthesisRequest
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider


PHRASES = (
    "Daxter est\u00e1 listo.",
    "Hola, Liam.",
    "Atlas est\u00e1 listo.",
    "Reinicia Telegram.",
    "Docker est\u00e1 funcionando.",
    "Enciende la luz del acuario peque\u00f1o.",
    "Home Assistant est\u00e1 conectado.",
    "Ma\u00f1ana a las dieciocho treinta revisar\u00e9 Atlas.",
)


def wav_metrics(path: Path) -> dict[str, object]:
    with wave.open(str(path), "rb") as audio:
        frames = audio.readframes(audio.getnframes())
        rate = audio.getframerate()
        count = audio.getnframes()
    samples = memoryview(frames).cast("h") if frames else ()
    tail_count = min(len(samples), max(1, int(rate * 0.005)))
    tail = samples[-tail_count:] if samples else ()
    return {
        "duration_seconds": round(count / rate, 3),
        "last_sample": abs(int(samples[-1])) if samples else 0,
        "final_5ms_peak": max((abs(int(item)) for item in tail), default=0),
        "final_5ms_rms": round(
            math.sqrt(sum(int(item) ** 2 for item in tail) / len(tail)), 3
        ) if tail else 0.0,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def generate(provider: ChatterboxDaxterProvider, output_dir: Path) -> list[dict[str, object]]:
    records = []
    for index, phrase in enumerate(PHRASES, 1):
        path = output_dir / f"{index:02d}.wav"
        started = perf_counter()
        result = provider.synthesize(SynthesisRequest(
            text=phrase,
            voice_id="daxter_official",
            provider_voice_id="daxter_es_jak2",
            output_path=path,
            voice_profile_id="daxter_es_jak2",
            profile_version="1.0.0",
        ))
        record = {
            "id": index,
            "text": phrase,
            "success": result.success,
            "latency_ms": round((perf_counter() - started) * 1000, 3),
            "cache_hit": result.cache_hit,
            "error": result.error,
        }
        if result.success:
            record.update(wav_metrics(path))
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    command = [str(args.python), str(ROOT / "tools" / "chatterbox_worker.py")]
    payload = {"phrases": list(PHRASES), "variants": {}}
    for name, enabled in (("version_actual", False), ("version_corregida", True)):
        target = args.output_dir / name
        target.mkdir(parents=True, exist_ok=True)
        provider = ChatterboxDaxterProvider(
            worker_command=command,
            cache_dir=args.output_dir / "cache" / name,
            postprocess=enabled,
        )
        try:
            payload["variants"][name] = generate(provider, target)
            payload["variants"][name + "_health"] = provider.health()
        finally:
            provider.close()
    (args.output_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if all(
        item["success"]
        for name in ("version_actual", "version_corregida")
        for item in payload["variants"][name]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
