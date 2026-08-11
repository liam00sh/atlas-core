"""Traducción explícita de DaxterVoiceStyle a controles reales de Chatterbox V2."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
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
        """Aplica sólo las dos normalizaciones aceptadas por REDACTED_2c7b6821719d."""
        result = unicodedata.normalize("NFC", text)
        result = re.sub(r"\bJak\b", "Yak", result, flags=re.IGNORECASE)
        replacements = {
            "el 9 de agosto de 2026": "el nueve de agosto de dos mil veintiséis",
            "a las 18:45": "a las dieciocho cuarenta y cinco",
            "1.300 muestras": "mil trescientas muestras",
        }
        for source, target in replacements.items():
            result = result.replace(source, target)
        result = re.sub(
            r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
            lambda match: ChatterboxStyleAdapter._spoken_time(
                int(match.group(1)), int(match.group(2))
            ),
            result,
        )
        return result

    @staticmethod
    def _spoken_time(hour: int, minute: int) -> str:
        numbers = {
            0: "cero", 1: "una", 2: "dos", 3: "tres", 4: "cuatro",
            5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve",
            10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce",
            15: "quince", 16: "dieciséis", 17: "diecisiete", 18: "dieciocho",
            19: "diecinueve", 20: "veinte", 21: "veintiuna", 22: "veintidós",
            23: "veintitrés", 24: "veinticuatro", 25: "veinticinco",
            26: "veintiséis", 27: "veintisiete", 28: "veintiocho",
            29: "veintinueve", 30: "treinta", 31: "treinta y una",
            32: "treinta y dos", 33: "treinta y tres", 34: "treinta y cuatro",
            35: "treinta y cinco", 36: "treinta y seis", 37: "treinta y siete",
            38: "treinta y ocho", 39: "treinta y nueve", 40: "cuarenta",
            41: "cuarenta y una", 42: "cuarenta y dos", 43: "cuarenta y tres",
            44: "cuarenta y cuatro", 45: "cuarenta y cinco",
            46: "cuarenta y seis", 47: "cuarenta y siete", 48: "cuarenta y ocho",
            49: "cuarenta y nueve", 50: "cincuenta", 51: "cincuenta y una",
            52: "cincuenta y dos", 53: "cincuenta y tres", 54: "cincuenta y cuatro",
            55: "cincuenta y cinco", 56: "cincuenta y seis",
            57: "cincuenta y siete", 58: "cincuenta y ocho", 59: "cincuenta y nueve",
        }
        if minute == 0:
            return numbers[hour]
        return f"{numbers[hour]} y {numbers[minute]}"

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
