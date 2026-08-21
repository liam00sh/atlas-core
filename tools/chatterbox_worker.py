"""Worker JSONL persistente para Chatterbox; se ejecuta en el venv Python 3.11."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import re
import sys
from contextlib import redirect_stdout


os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["NO_PROXY"] = "*"
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_MODEL = None
_CANDIDATE = os.getenv("ATLAS_CHATTERBOX_CANDIDATE", "v2").strip().casefold()

from tools.chatterbox_es_es_runtime import cap_generation, load_es_es_model


def generation_controls(controls: dict, reference_path: str, *, candidate: str | None = None) -> dict:
    selected = _CANDIDATE if candidate is None else candidate
    kwargs = {
        "language_id": "es" if selected == "es_es" else controls["language_id"],
        "audio_prompt_path": reference_path,
        "exaggeration": 0.45 if selected == "es_es" else controls["exaggeration"],
        "cfg_weight": 0.35 if selected == "es_es" else controls["cfg_weight"],
        "temperature": 0.8 if selected == "es_es" else controls["temperature"],
    }
    if selected != "es_es":
        kwargs.update(
            repetition_penalty=controls["repetition_penalty"],
            min_p=controls["min_p"], top_p=controls["top_p"],
        )
    return kwargs


def _split_tts_units(text: str, *, max_chars: int = 220) -> list[str]:
    """Split long input at linguistic boundaries before the model sees it."""
    sentences = [
        item.strip()
        for item in re.findall(r".*?(?:[.!?](?=\s|$)|$)", text, flags=re.DOTALL)
        if item.strip()
    ]
    parts: list[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            parts.append(sentence)
            continue
        clauses = [item.strip() for item in re.split(r"(?<=[,;:])\s+", sentence) if item.strip()]
        current = ""
        for clause in clauses:
            if len(clause) > max_chars:
                words = clause.split()
                word_chunk = ""
                for word in words:
                    word_candidate = f"{word_chunk} {word}".strip()
                    if word_chunk and len(word_candidate) > max_chars:
                        if current:
                            parts.append(current)
                            current = ""
                        parts.append(word_chunk)
                        word_chunk = word
                    else:
                        word_chunk = word_candidate
                clause = word_chunk
            candidate = f"{current} {clause}".strip()
            if current and len(candidate) > max_chars:
                parts.append(current)
                current = clause
            else:
                current = candidate
        if current:
            parts.append(current)

    units: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}".strip()
        if current and len(candidate) > max_chars:
            units.append(current)
            current = part
        else:
            current = candidate
    if current:
        units.append(current)
    return units or [text.strip()]


def generation_budget(text: str, policy: dict | None = None) -> int:
    """Presupuesta voz a 25 tokens/s sin volver al techo abierto de 1000."""
    policy = dict(policy or {})
    fixed = policy.get("fixed_max_new_tokens")
    if fixed is not None:
        return max(1, int(fixed))
    floor = max(1, int(policy.get("floor", 120)))
    ceiling = max(floor, int(policy.get("ceiling", 260)))
    tokens_per_char = max(0.1, float(policy.get("tokens_per_char", 2.0)))
    punctuation_bonus = max(0, int(policy.get("punctuation_bonus", 4)))
    digit_bonus = max(0, int(policy.get("digit_bonus", 2)))
    punctuation = sum(text.count(mark) for mark in ".,;:!?¡¿")
    digits = sum(ch.isdigit() for ch in text)
    estimated = round(len(text) * tokens_per_char) + punctuation * punctuation_bonus + digits * digit_bonus
    return min(ceiling, max(floor, estimated))


def _trim_and_fade(audio, sample_rate: int, options: dict | None = None):
    """Conservatively protect phonemes and only fade inside retained padding."""
    import torch

    options = dict(options or {})
    trim_start = bool(options.get("trim_start", False))
    trim_end = bool(options.get("trim_end", True))
    threshold = max(0.0, float(options.get("threshold", 0.0005)))
    start_padding = int(sample_rate * max(0.0, float(options.get("start_padding_ms", 80))) / 1000)
    end_padding = int(sample_rate * max(0.0, float(options.get("end_padding_ms", 80))) / 1000)
    ensure_end_padding = bool(options.get("ensure_end_padding", True))
    pre_roll = int(sample_rate * max(0.0, float(options.get("pre_roll_ms", 0))) / 1000)
    fade_ms = max(0.0, float(options.get("fade_ms", 5)))
    if audio.ndim == 1:
        audio = audio.unsqueeze(0)
    mono_peak = audio.abs().amax(dim=0)
    active = torch.nonzero(mono_peak > threshold, as_tuple=False).flatten()
    if active.numel():
        start = max(0, int(active[0]) - start_padding) if trim_start else 0
        desired_end = int(active[-1]) + end_padding + 1
        end = min(audio.shape[-1], desired_end) if trim_end else audio.shape[-1]
        audio = audio[:, start:end]
        if trim_end and ensure_end_padding and desired_end > end:
            missing = desired_end - end
            audio = torch.cat(
                (audio, torch.zeros((audio.shape[0], missing), device=audio.device)),
                dim=-1,
            )
    if pre_roll:
        audio = torch.cat(
            (torch.zeros((audio.shape[0], pre_roll), device=audio.device), audio),
            dim=-1,
        )
    fade = min(int(sample_rate * fade_ms / 1000), audio.shape[-1] // 2)
    if fade > 1:
        audio[:, :fade] *= torch.linspace(0.0, 1.0, fade, device=audio.device)
        audio[:, -fade:] *= torch.linspace(1.0, 0.0, fade, device=audio.device)
    return audio


def synthesize(payload: dict) -> dict:
    global _MODEL
    import numpy as np
    import torch
    import torchaudio
    from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter
    from voice.style import VoiceStyleSelector

    if _MODEL is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if _CANDIDATE == "es_es":
            source = Path(os.environ["ATLAS_CHATTERBOX_SOURCE"]).resolve()
            model_dir = Path(os.environ["ATLAS_CHATTERBOX_MODEL_DIR"]).resolve()
            _MODEL, _route = load_es_es_model(source=source, model_dir=model_dir, device=device)
        else:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            _MODEL = ChatterboxMultilingualTTS.from_pretrained(device=device)
    seed = int(payload["seed"])
    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    catalog = Path(payload["catalog_path"])
    profile = Path(payload["profile_path"])
    selector = VoiceStyleSelector(catalog)
    adapter = ChatterboxStyleAdapter(catalog, profile)
    style = selector.resolve(payload["emotion"], payload["intensity"])
    controls = adapter.to_tts_style(style)
    output = Path(payload["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized_text = adapter.normalize_text(payload["text"])
    units = _split_tts_units(normalized_text)
    generated = []
    generation_units = []
    for index, unit in enumerate(units):
        unit_seed = seed + index
        random.seed(unit_seed)
        np.random.seed(unit_seed % (2**32 - 1))
        torch.manual_seed(unit_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(unit_seed)
        kwargs = generation_controls(controls, payload["reference_path"])
        if _CANDIDATE == "es_es":
            _MODEL._atlas_max_new_tokens = generation_budget(
                unit, payload.get("generation_policy")
            )
            _MODEL._atlas_last_generation = None
        generated.append(_MODEL.generate(unit, **kwargs))
        metrics = dict(getattr(_MODEL, "_atlas_last_generation", None) or {})
        metrics.update({"unit_index": index, "chars": len(unit)})
        generation_units.append(metrics)
    gap = torch.zeros((generated[0].shape[0], int(_MODEL.sr * 0.06)), device=generated[0].device)
    parts = []
    for index, item in enumerate(generated):
        if index:
            parts.append(gap)
        parts.append(item)
    audio = torch.cat(parts, dim=-1)
    raw_output = payload.get("diagnostic_raw_output_path")
    if raw_output:
        raw_path = Path(str(raw_output))
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(raw_path), audio.cpu(), _MODEL.sr, encoding="PCM_S", bits_per_sample=16)
    if payload.get("postprocess", True):
        audio = _trim_and_fade(audio, _MODEL.sr, payload.get("postprocess_options"))
    torchaudio.save(str(output), audio.cpu(), _MODEL.sr, encoding="PCM_S", bits_per_sample=16)
    return {
        "success": True,
        "emotion": style.emotion,
        "intensity": style.intensity.value,
        "chars_synthesized": len(normalized_text),
        "synthesized_samples": int(audio.shape[-1]),
        "wav_duration_ms": round(audio.shape[-1] / _MODEL.sr * 1000, 3),
        "tts_units": len(units),
        "generation_units": generation_units,
        "generation_tokens_budgeted": sum(int(item.get("tokens_budgeted", 0)) for item in generation_units),
        "generation_tokens_used": sum(int(item.get("tokens_used", 0)) for item in generation_units),
        "reached_generation_limit": any(bool(item.get("reached_generation_limit")) for item in generation_units),
        "runtime": {
            "python": sys.executable,
            "source": str(Path(os.environ.get("ATLAS_CHATTERBOX_SOURCE", "")).resolve()),
            "model_dir": str(Path(os.environ.get("ATLAS_CHATTERBOX_MODEL_DIR", "")).resolve()),
            "module": str(Path(sys.modules[_MODEL.__class__.__module__].__file__).resolve()),
            "device": str(_MODEL.device),
            "offline": True,
        },
    }


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")
    for line in sys.stdin:
        try:
            payload = json.loads(line)
            with redirect_stdout(sys.stderr):
                result = synthesize(payload)
        except Exception as exc:
            result = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        print("ATLAS_JSON:" + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
