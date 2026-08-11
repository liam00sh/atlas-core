"""Traducción explícita de DaxterVoiceStyle a controles reales de Chatterbox V2."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from voice.style import DaxterVoiceStyle


class ChatterboxStyleAdapter:
    def __init__(self, catalog_path: Path, profile_path: Path):
        catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        self._emotions = {item["id"]: item for item in catalog["emotions"]}
        self._profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))

    @staticmethod
    def stable_seed(base_seed: int, style_key: str, text: str) -> int:
        digest = hashlib.sha256(f"{base_seed}|{style_key}|{text}".encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big")

    @staticmethod
    def normalize_text(text: str) -> str:
        """Aplica sólo las dos normalizaciones aceptadas por Alex."""
        result = re.sub(r"\bJak\b", "Yak", text, flags=re.IGNORECASE)
        replacements = {
            "el 9 de agosto de 2026": "el nueve de agosto de dos mil veintiséis",
            "a las 18:45": "a las dieciocho cuarenta y cinco",
            "1.300 muestras": "mil trescientas muestras",
        }
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result

    def to_tts_style(self, style: DaxterVoiceStyle, *, reference_available: bool = True) -> dict:
        item = self._emotions.get(style.emotion, self._emotions["neutral"])
        reference_strategy = item["reference_audio_strategy"] if reference_available else "winner_jak2_diverse_identity_first"
        reason = style.reason
        if not reference_available:
            reason += "; referencia solicitada ausente, fallback a referencia neutral ganadora"
        return {
            "provider": "chatterbox_multilingual_v2",
            "language_id": self._profile["language_id"],
            "reference_strategy": reference_strategy,
            "reference_file": self._profile["reference_file"],
            "exaggeration": item["exaggeration"][style.intensity.value],
            "cfg_weight": item["cfg_weight"],
            "temperature": item["temperature"],
            "repetition_penalty": item["repetition_penalty"],
            "min_p": item["min_p"],
            "top_p": item["top_p"],
            "reason": reason,
        }
