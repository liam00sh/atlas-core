"""Worker JSONL persistente para Chatterbox; se ejecuta en el venv Python 3.11."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
from contextlib import redirect_stdout


os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["NO_PROXY"] = "*"
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_MODEL = None


def synthesize(payload: dict) -> dict:
    global _MODEL
    import numpy as np
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter
    from voice.style import VoiceStyleSelector

    if _MODEL is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
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
    audio = _MODEL.generate(
        adapter.normalize_text(payload["text"]),
        language_id=controls["language_id"],
        audio_prompt_path=payload["reference_path"],
        exaggeration=controls["exaggeration"],
        cfg_weight=controls["cfg_weight"],
        temperature=controls["temperature"],
        repetition_penalty=controls["repetition_penalty"],
        min_p=controls["min_p"],
        top_p=controls["top_p"],
    )
    torchaudio.save(str(output), audio.cpu(), _MODEL.sr, encoding="PCM_S", bits_per_sample=16)
    return {"success": True, "emotion": style.emotion, "intensity": style.intensity.value}


def main() -> int:
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
