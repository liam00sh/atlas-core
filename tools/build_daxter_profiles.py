"""Deriva catálogos de emoción y personalidad del maestro humano de Daxter."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


EMOTIONS = (
    "neutral", "sonriente", "picaro", "sorprendido", "pensativo", "emocionado",
    "asustado", "enfadado", "curioso", "confiado", "risa", "cansado",
    "sonoliento", "determinado", "travieso",
)
DISPLAY_NAMES = {
    "neutral": "Neutral", "sonriente": "Sonriente", "picaro": "Pícaro",
    "sorprendido": "Sorprendido", "pensativo": "Pensativo", "emocionado": "Emocionado",
    "asustado": "Asustado", "enfadado": "Enfadado", "curioso": "Curioso",
    "confiado": "Confiado", "risa": "Risa", "cansado": "Cansado",
    "sonoliento": "Soñoliento", "determinado": "Determinado", "travieso": "Travieso",
}
FALLBACKS = {
    "sonoliento": "cansado", "risa": "sonriente", "travieso": "picaro",
    "pensativo": "neutral", "cansado": "neutral",
}
TRAIT_RULES = {
    "humor": {"tags": {"humor"}, "emotions": {"risa"}},
    "sarcasmo": {"tags": {"sarcasmo"}},
    "picardia": {"tags": {"travieso", "burla"}, "emotions": {"picaro", "travieso"}},
    "dramatismo": {"tags": {"dramatico"}},
    "fanfarroneria": {"tags": {"presumido", "autorreferencial"}},
    "quejas": {"tags": {"quejica"}, "intentions": {"queja"}},
    "nerviosismo": {"tags": {"cobarde_comico"}, "emotions": {"asustado"}},
    "miedo": {"emotions": {"asustado"}},
    "entusiasmo": {"tags": {"entusiasta"}, "emotions": {"emocionado"}},
    "curiosidad": {"tags": {"curioso"}, "emotions": {"curioso"}},
    "confianza": {"emotions": {"confiado"}},
    "impulsividad": {"tags": {"impulsivo"}},
    "lealtad": {"tags": {"leal"}},
    "afecto": {"tags": {"afectivo"}},
    "burla": {"tags": {"burla"}, "intentions": {"burla"}},
    "exageracion": {"tags": {"dramatico", "entusiasta"}},
    "comentarios_secundarios": {"tags": {"charlatan"}},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1300 or len({row["sample_id"] for row in rows}) != 1300:
        raise ValueError("El maestro debe conservar 1.300 sample_id únicos")
    return rows


def split_tags(value: str) -> set[str]:
    normalized = value.replace(",", "|").replace(";", "|")
    return {item.strip().casefold() for item in normalized.split("|") if item.strip()}


def reference_score(row: dict) -> tuple:
    duration = float(row["duration_seconds"])
    return (
        row["quality"].casefold() == "buena",
        row["emotion_confidence"].casefold() == "alta",
        row["emotion_source"].casefold() == "human",
        str(row["personality_usable"]).casefold() == "true",
        row["context_confidence"].casefold() == "alta",
        1.25 <= duration <= 7.0,
        row["source_game"].casefold() == "jak2",
        -abs(duration - 3.5),
        row["sample_id"],
    )


def supported_intensities(rows: list[dict]) -> list[str]:
    counts = Counter(row["emotion_intensity"].casefold() for row in rows)
    return [level for level in ("baja", "media", "alta") if counts[level] >= 2]


def build_emotion_catalog(rows: list[dict], source_hash: str, winner_profile: dict) -> dict:
    items = []
    for emotion in EMOTIONS:
        subset = [row for row in rows if row["emotion"].casefold() == emotion]
        references = sorted(subset, key=reference_score, reverse=True)[:5]
        energies = Counter(row["energy"].casefold() for row in subset)
        intensities = Counter(row["emotion_intensity"].casefold() for row in subset)
        intentions = Counter(row["intention"].casefold() for row in subset)
        supported = supported_intensities(subset)
        if not supported:
            supported = ["baja", "media"] if emotion == "sonoliento" else ["media"]
        preferred = energies.most_common(1)[0][0] if energies else "baja"
        notes = []
        if emotion == "sonoliento":
            notes.append("No existen muestras etiquetadas como sonoliento; usa fallback cansado y requiere validación humana.")
        if emotion == "risa":
            notes.append("Sólo hay cuatro muestras; se usan interjecciones breves, nunca carcajadas largas sintetizadas.")
        notes.append("La referencia activa sigue siendo la diversa ganadora B1: B3 demostró que referencias emocionales dinámicas reducían identidad.")
        items.append({
            "id": emotion,
            "display_name": DISPLAY_NAMES[emotion],
            "dataset_evidence": {
                "examples": len(subset),
                "minutes": round(sum(float(row["duration_seconds"]) for row in subset) / 60, 4),
                "energy_counts": dict(energies),
                "intensity_counts": dict(intensities),
                "intention_counts": dict(intentions.most_common()),
            },
            "reference_samples": [
                {
                    "sample_id": row["sample_id"],
                    "audio_file": row["audio_file"],
                    "duration_seconds": float(row["duration_seconds"]),
                    "quality": row["quality"],
                    "emotion_confidence": row["emotion_confidence"],
                }
                for row in references
            ],
            "reference_audio_strategy": "winner_jak2_diverse_identity_first",
            "exaggeration": {"baja": 0.45, "media": 0.55, "alta": 0.65},
            "cfg_weight": 0.35,
            "temperature": 0.8,
            "repetition_penalty": 2.0,
            "min_p": 0.05,
            "top_p": 1.0,
            "preferred_energy": preferred,
            "supported_intensities": supported,
            "fallback_emotion": FALLBACKS.get(emotion, "neutral"),
            "notes": notes,
        })
    return {
        "catalog_id": "daxter_emotions_v1",
        "version": "1.0.0-provisional",
        "status": "pending_human_emotion_validation",
        "source_metadata_sha256": source_hash,
        "winner_profile": winner_profile["profile_id"],
        "parameter_basis": {
            "low": "B1 neutral/confident human-tested anchor, exaggeration 0.45",
            "high": "B1 expressive human-tested anchor, exaggeration 0.65",
            "medium": "deterministic midpoint 0.55; pending direct human intensity validation",
            "other_controls": "Frozen B1 values; no random per-emotion tuning",
        },
        "emotions": items,
    }


def trait_match(row: dict, rule: dict) -> bool:
    tags = split_tags(row["personality_tags"])
    return bool(
        tags & rule.get("tags", set())
        or row["emotion"].casefold() in rule.get("emotions", set())
        or row["intention"].casefold() in rule.get("intentions", set())
    )


def build_personality_profile(rows: list[dict], source_hash: str) -> dict:
    word_counts = [len(row["text"].split()) for row in rows]
    traits = {}
    for trait, rule in TRAIT_RULES.items():
        matches = [row for row in rows if trait_match(row, rule)]
        traits[trait] = {
            "supported": len(matches) >= 3,
            "samples": len(matches),
            "share": round(len(matches) / len(rows), 4),
            "evidence_sample_ids": [row["sample_id"] for row in sorted(matches, key=reference_score, reverse=True)[:5]],
        }
    return {
        "profile_id": "daxter_personality_v1",
        "version": "1.0.0-provisional",
        "status": "offline_human_validation_pending",
        "source_metadata_sha256": source_hash,
        "source_rows": len(rows),
        "principle": "Atlas gobierna los hechos y acciones; este perfil sólo gobierna cómo se expresan.",
        "traits": traits,
        "speech_length": {
            "mean_words": round(statistics.mean(word_counts), 2),
            "median_words": statistics.median(word_counts),
            "p90_words": sorted(word_counts)[math.ceil(0.90 * len(word_counts)) - 1],
            "max_words": max(word_counts),
        },
        "strength_levels": {
            "low": "Sin adorno o una marca mínima; obligatorio para emergencia, privacidad, seguridad y conducción.",
            "normal": "Un comentario breve opcional sin alterar la respuesta base.",
            "high": "Más energía y humor, sólo en conversación casual y sin ocultar la respuesta base.",
        },
        "hard_rules": [
            "Conservar literalmente la respuesta base dentro de la salida estilizada.",
            "Nunca cambiar hechos, cifras, permisos, resultado de acciones o incertidumbre.",
            "Emergencia y conducción fuerzan low; privacidad y seguridad fuerzan low.",
            "No usar diálogos del juego como motor de respuestas.",
            "No añadir humor cuando pueda distraer, minimizar riesgo o degradar claridad.",
        ],
        "expression_guidance": {
            "normal": ["energía breve", "humor ocasional", "picardía moderada", "una sola observación secundaria como máximo"],
            "avoid": ["citas de juego fuera de contexto", "muletillas repetitivas", "caricatura constante", "bromas en cada respuesta"],
        },
    }


def personality_markdown(profile: dict, rows: list[dict]) -> str:
    emotion_counts = Counter(row["emotion"] for row in rows)
    intention_counts = Counter(row["intention"] for row in rows)
    lines = [
        "# Análisis de personalidad de Daxter",
        "",
        f"Base: 1.300 transcripciones humanas; SHA-256 `{profile['source_metadata_sha256']}`. Los diálogos se usan como evidencia estadística, no como banco de respuestas.",
        "",
        "## Rasgos respaldados",
        "",
        "| Rasgo | Muestras | Proporción | Evidencia interna |",
        "|---|---:|---:|---|",
    ]
    for name, item in profile["traits"].items():
        if item["supported"]:
            lines.append(f"| {name} | {item['samples']} | {item['share']:.1%} | {', '.join(item['evidence_sample_ids'])} |")
    lines.extend([
        "",
        "## Distribución contextual",
        "",
        "Emociones más frecuentes: " + ", ".join(f"{name}={count}" for name, count in emotion_counts.most_common(8)) + ".",
        "",
        "Intenciones más frecuentes: " + ", ".join(f"{name}={count}" for name, count in intention_counts.most_common(8)) + ".",
        "",
        "## Longitud",
        "",
        f"Media {profile['speech_length']['mean_words']} palabras; mediana {profile['speech_length']['median_words']}; percentil 90 {profile['speech_length']['p90_words']}. El adaptador debe favorecer intervenciones cortas.",
        "",
        "## Límite operativo",
        "",
        "La primera versión es un adaptador reversible y offline. Conserva literalmente el contenido base de Atlas, reduce personalidad según riesgo y no entrena ningún LLM.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--winner-profile", type=Path, required=True)
    parser.add_argument("--emotion-output", type=Path, required=True)
    parser.add_argument("--personality-output", type=Path, required=True)
    parser.add_argument("--analysis-output", type=Path, required=True)
    args = parser.parse_args()
    metadata = args.metadata.resolve()
    rows = load_metadata(metadata)
    source_hash = sha256_file(metadata)
    winner = json.loads(args.winner_profile.read_text(encoding="utf-8"))
    emotion_catalog = build_emotion_catalog(rows, source_hash, winner)
    personality = build_personality_profile(rows, source_hash)
    for path in (args.emotion_output, args.personality_output, args.analysis_output):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.emotion_output.write_text(json.dumps(emotion_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.personality_output.write_text(json.dumps(personality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.analysis_output.write_text(personality_markdown(personality, rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "emotions": len(emotion_catalog["emotions"]), "traits": len(personality["traits"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
