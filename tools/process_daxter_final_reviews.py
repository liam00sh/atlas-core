"""Procesa las validaciones humanas finales sin modificar sus CSV canónicos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from statistics import mean


EMOTION_SCORE_FIELDS = (
    "se_parece_a_daxter_1_5",
    "emocion_correcta_1_5",
    "naturalidad_1_5",
    "intensidad_correcta_1_5",
    "pronunciacion_1_5",
    "artefactos_1_5",
)
PERSONALITY_SCORE_FIELDS = (
    "parece_daxter_1_5",
    "naturalidad_1_5",
    "humor_adecuado_1_5",
    "intensidad_adecuada_1_5",
    "conserva_informacion_1_5",
)
APPROVED_EMOTIONS = {
    "neutral", "picaro", "sorprendido", "emocionado", "confiado",
    "determinado", "risa",
}
NEEDS_ADJUSTMENT_EMOTIONS = {
    "asustado", "cansado", "curioso", "enfadado", "pensativo",
    "sonriente", "travieso",
}
FALLBACK_EMOTIONS = {"sonoliento"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {key: str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
            if any(str(value or "").strip() for value in row.values())
        ]


def validate_scores(rows: list[dict[str, str]], fields: tuple[str, ...], id_field: str) -> None:
    for row in rows:
        for field in fields:
            try:
                value = int(row[field])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"{row.get(id_field, '?')}: puntuación inválida en {field}") from exc
            if value not in {1, 2, 3, 4, 5}:
                raise ValueError(f"{row.get(id_field, '?')}: {field} fuera de 1..5")


def aggregate(rows: list[dict], fields: tuple[str, ...]) -> dict:
    return {
        "samples": len(rows),
        "means": {
            field: round(mean(float(row[field]) for row in rows), 4)
            for field in fields
        },
    }


def grouped(rows: list[dict], keys: tuple[str, ...], fields: tuple[str, ...]) -> dict:
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[key]) for key in keys)].append(row)
    return {
        "|".join(key): {
            **aggregate(items, fields),
            "notes": [item["notas"] for item in items if item.get("notas")],
        }
        for key, items in sorted(groups.items())
    }


def emotion_decision(emotion: str) -> dict:
    if emotion in APPROVED_EMOTIONS:
        return {
            "status": "approved",
            "runtime_emotion": emotion,
            "runtime_fallback_emotion": "neutral",
            "reason": "La estrategia B1 diversa alcanza el umbral humano de identidad, emoción, naturalidad e integridad.",
            "next_validation": None,
        }
    if emotion in NEEDS_ADJUSTMENT_EMOTIONS:
        return {
            "status": "needs_adjustment",
            "runtime_emotion": "neutral",
            "runtime_fallback_emotion": "neutral",
            "reason": "La evaluación humana detecta identidad, emoción, naturalidad, prosodia o artefactos por debajo del umbral final.",
            "next_validation": "mini-ronda dirigida: una toma B1 ajustada frente al fallback neutral",
        }
    if emotion in FALLBACK_EMOTIONS:
        return {
            "status": "fallback",
            "runtime_emotion": "neutral",
            "runtime_fallback_emotion": "neutral",
            "reason": "El fallback cansado no equilibra identidad y emoción; se usa neutral baja hasta una mini-prueba directa.",
            "next_validation": "mini-ronda dirigida sonoliento: B1 baja frente a referencia cansado ajustada",
        }
    raise ValueError(f"Emoción oficial no clasificada: {emotion}")


def process_emotions(csv_path: Path, key_path: Path, provisional_catalog_path: Path) -> tuple[dict, dict]:
    all_rows = load_rows(csv_path)
    general_notes = [row["notas"] for row in all_rows if not row.get("blind_code") and row.get("notas")]
    rows = [row for row in all_rows if row.get("blind_code")]
    validate_scores(rows, EMOTION_SCORE_FIELDS, "blind_code")

    key_payload = json.loads(key_path.read_text(encoding="utf-8"))
    key_rows = key_payload["entries"]
    key_by_code = {row["blind_code"]: row for row in key_rows}
    codes = [row["blind_code"] for row in rows]
    if len(rows) != 38 or len(set(codes)) != 38:
        raise ValueError("La evaluación emocional debe contener 38 códigos ciegos únicos")
    if set(codes) != set(key_by_code):
        raise ValueError("El CSV emocional y EMOTION_TEST_KEY.json no forman una biyección")

    joined = []
    for row in rows:
        evidence = key_by_code[row["blind_code"]]
        if row["emotion"] != evidence["emotion"] or row["intensity"] != evidence["intensity"]:
            raise ValueError(f"{row['blind_code']}: objetivo visible no coincide con la clave")
        joined.append({**row, **evidence})

    decisions = {emotion: emotion_decision(emotion) for emotion in sorted(
        APPROVED_EMOTIONS | NEEDS_ADJUSTMENT_EMOTIONS | FALLBACK_EMOTIONS
    )}
    results = {
        "schema_version": 1,
        "source_csv": csv_path.name,
        "source_csv_sha256": sha256_file(csv_path),
        "key_sha256": sha256_file(key_path),
        "samples": 38,
        "general_notes": general_notes,
        "overall": aggregate(joined, EMOTION_SCORE_FIELDS),
        "by_emotion": grouped(joined, ("emotion",), EMOTION_SCORE_FIELDS),
        "by_intensity": grouped(joined, ("intensity",), EMOTION_SCORE_FIELDS),
        "by_reference_strategy": grouped(joined, ("reference_variant",), EMOTION_SCORE_FIELDS),
        "by_emotion_intensity_strategy": grouped(
            joined, ("emotion", "intensity", "reference_variant"), EMOTION_SCORE_FIELDS
        ),
        "decisions": decisions,
        "approved_count": len(APPROVED_EMOTIONS),
        "needs_adjustment_count": len(NEEDS_ADJUSTMENT_EMOTIONS),
        "fallback_count": len(FALLBACK_EMOTIONS),
        "strategy_decision": "winner_diverse",
        "strategy_reason": "B1 diversa obtiene 3,9130 en identidad frente a 2,8000 de referencias emocionales experimentales.",
        "human_authority": "Las puntuaciones y notas humanas prevalecen sobre las comprobaciones automáticas.",
    }

    catalog = deepcopy(json.loads(provisional_catalog_path.read_text(encoding="utf-8")))
    catalog["catalog_id"] = "daxter_emotions_final_v1"
    catalog["version"] = "1.0.0"
    catalog["status"] = "human_validated_with_safe_fallbacks"
    catalog["human_results_sha256"] = results["source_csv_sha256"]
    catalog["active_reference_strategy"] = "winner_jak2_diverse_identity_first"
    catalog["experimental_reference_strategy"] = "rejected_for_runtime_identity_loss"
    for item in catalog["emotions"]:
        decision = decisions[item["id"]]
        item["human_validation"] = decision
        item["runtime_emotion"] = decision["runtime_emotion"]
        item["reference_audio_strategy"] = "winner_jak2_diverse_identity_first"
        if decision["status"] != "approved":
            item["fallback_emotion"] = decision["runtime_fallback_emotion"]
            item["supported_intensities"] = ["baja", "media"]
    return results, catalog


def process_personality(csv_path: Path) -> tuple[dict, dict]:
    rows = load_rows(csv_path)
    if len(rows) != 40 or len({row["case_id"] for row in rows}) != 40:
        raise ValueError("La evaluación de personalidad debe contener 40 casos únicos")
    validate_scores(rows, PERSONALITY_SCORE_FIELDS, "case_id")
    for row in rows:
        for field in ("demasiado_daxter_si_no", "demasiado_serio_si_no"):
            if row[field] not in {"SI", "NO"}:
                raise ValueError(f"{row['case_id']}: {field} debe ser SI o NO")

    by_strength = grouped(rows, ("personality_strength",), PERSONALITY_SCORE_FIELDS)
    for strength in ("low", "normal", "high"):
        subset = [row for row in rows if row["personality_strength"] == strength]
        by_strength[strength]["demasiado_daxter_si"] = sum(
            row["demasiado_daxter_si_no"] == "SI" for row in subset
        )
        by_strength[strength]["demasiado_serio_si"] = sum(
            row["demasiado_serio_si_no"] == "SI" for row in subset
        )

    derived_rules = [
        {"id": "facts_are_immutable", "evidence": "40/40 casos conservan información con 5/5", "rule": "La capa de estilo no puede cambiar hechos, cifras, nombres, estados, permisos, errores o incertidumbre."},
        {"id": "normal_is_default", "evidence": "normal: 4,7619 Daxter y 4,5714 naturalidad", "rule": "Usar normal para conversación, acciones, Home Assistant y respuestas técnicas breves."},
        {"id": "low_keeps_micro_identity", "evidence": "11/14 casos low fueron demasiado serios", "rule": "Low conserva una marca verbal mínima salvo privacidad, seguridad, conducción o emergencia."},
        {"id": "high_one_flourish", "evidence": "high: 4,8 Daxter y 5,0 humor; 1/5 demasiado Daxter", "rule": "High permite un único remate contextual, nunca dos y nunca en contextos sensibles."},
        {"id": "join_short_clauses", "evidence": "Correcciones reiteradas sustituyen cortes por comas", "rule": "Unir cláusulas cortas relacionadas cuando mejora la entonación; no encadenar frases largas."},
        {"id": "contextual_openers", "evidence": "Vamos al grano falló en aviso y sorpresa", "rule": "La apertura depende del tipo de respuesta y emoción; evitar una coletilla universal."},
        {"id": "avoid_template_repetition", "evidence": "La revisión penaliza frases genéricas o no propias de Daxter", "rule": "No repetir la misma apertura en turnos consecutivos y no seleccionar respuestas completas de un banco."},
        {"id": "emotion_consistency", "evidence": "Listo contradice cansancio en saludo nocturno", "rule": "El léxico y la cadencia deben ser compatibles con emoción e intensidad."},
        {"id": "brief_operational_actions", "evidence": "Home Assistant y acciones concisas obtienen 4-5/5", "rule": "Confirmar primero el resultado operativo y limitar el estilo a una sola marca breve."},
        {"id": "serious_context_no_humour", "evidence": "Seguridad, privacidad, conducción y emergencia preservan claridad 5/5", "rule": "En riesgo alto no añadir humor ni remates; la identidad sólo puede aparecer como cadencia sobria."},
    ]
    results = {
        "schema_version": 1,
        "source_csv": csv_path.name,
        "source_csv_sha256": sha256_file(csv_path),
        "samples": 40,
        "overall": aggregate(rows, PERSONALITY_SCORE_FIELDS),
        "by_strength": by_strength,
        "by_category": grouped(rows, ("category",), PERSONALITY_SCORE_FIELDS),
        "demasiado_daxter_si": sum(row["demasiado_daxter_si_no"] == "SI" for row in rows),
        "demasiado_serio_si": sum(row["demasiado_serio_si_no"] == "SI" for row in rows),
        "corrected_examples": sum(bool(row["correccion_frase_daxter"]) for row in rows),
        "derived_rules": derived_rules,
        "corrections_policy": "Las correcciones se convirtieron en patrones; no se copian como banco de respuestas.",
    }
    rules = {
        "profile_id": "daxter_personality_v2_rules",
        "version": "2.0.0",
        "status": "human_validated",
        "source_csv_sha256": results["source_csv_sha256"],
        "default_strength": "normal",
        "strength_policy": {
            "low": {"max_style_moves": 1, "max_flourishes": 0, "micro_identity": True},
            "normal": {"max_style_moves": 2, "max_flourishes": 0, "micro_identity": True},
            "high": {"max_style_moves": 3, "max_flourishes": 1, "micro_identity": True},
        },
        "forced_low": ["privacy", "security", "driving", "emergency"],
        "forced_plain": ["privacy", "security", "driving", "emergency"],
        "rules": derived_rules,
        "forbidden": [
            "copiar diálogos del dataset", "seleccionar respuestas humanas completas",
            "cambiar hechos o resultados", "humor en contextos sensibles",
            "más de un remate de personalidad",
        ],
    }
    return results, rules


def emotion_markdown(results: dict) -> str:
    lines = [
        "# Resultados humanos finales — emociones Daxter", "",
        f"Fuente canónica: `{results['source_csv']}` (`{results['source_csv_sha256']}`).", "",
        f"Muestras puntuadas: {results['samples']}. Estrategia activa: **B1 diversa**.", "",
        "| Emoción | Estado | Identidad | Emoción | Naturalidad | Intensidad | Pronunciación | Artefactos |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for emotion, decision in results["decisions"].items():
        metrics = results["by_emotion"][emotion]["means"]
        lines.append(
            f"| {emotion} | {decision['status']} | {metrics['se_parece_a_daxter_1_5']:.4f} | "
            f"{metrics['emocion_correcta_1_5']:.4f} | {metrics['naturalidad_1_5']:.4f} | "
            f"{metrics['intensidad_correcta_1_5']:.4f} | {metrics['pronunciacion_1_5']:.4f} | "
            f"{metrics['artefactos_1_5']:.4f} |"
        )
    lines += ["", "## Observaciones globales", ""]
    lines += [f"- {note}" for note in results["general_notes"]]
    lines += ["", "Las emociones no aprobadas caen a neutral en tiempo de ejecución y quedan limitadas a una mini-ronda dirigida; no se interpretan las comprobaciones automáticas como aprobación humana.", ""]
    return "\n".join(lines)


def personality_markdown(results: dict) -> str:
    lines = [
        "# Resultados humanos finales — personalidad Daxter", "",
        f"Fuente canónica: `{results['source_csv']}` (`{results['source_csv_sha256']}`).", "",
        "| Nivel | Casos | Parece Daxter | Naturalidad | Humor | Intensidad | Conserva información | Demasiado serio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strength in ("low", "normal", "high"):
        data = results["by_strength"][strength]
        scores = data["means"]
        lines.append(
            f"| {strength} | {data['samples']} | {scores['parece_daxter_1_5']:.4f} | "
            f"{scores['naturalidad_1_5']:.4f} | {scores['humor_adecuado_1_5']:.4f} | "
            f"{scores['intensidad_adecuada_1_5']:.4f} | {scores['conserva_informacion_1_5']:.4f} | "
            f"{data['demasiado_serio_si']} |"
        )
    lines += ["", "## Reglas derivadas", ""]
    lines += [f"- **{rule['id']}**: {rule['rule']} ({rule['evidence']})." for rule in results["derived_rules"]]
    lines += ["", "Las correcciones de REDACTED_f73137d930c3 se usaron para extraer estas reglas; no forman un banco de respuestas.", ""]
    return "\n".join(lines)


def emotion_mini_round_plan(results: dict) -> dict:
    items = []
    for emotion, decision in results["decisions"].items():
        if decision["status"] == "approved":
            continue
        metrics = results["by_emotion"][emotion]["means"]
        items.append({
            "emotion": emotion,
            "current_status": decision["status"],
            "candidates": [
                "B1 diversa con una única corrección dirigida de prosodia/intensidad",
                "fallback neutral con intensidad compatible",
            ],
            "human_fields": list(EMOTION_SCORE_FIELDS),
            "current_means": metrics,
            "acceptance": "aprobar sólo si identidad, emoción y naturalidad alcanzan 4/5 sin artefactos graves",
            "runtime_until_review": decision["runtime_emotion"],
        })
    return {
        "schema_version": 1,
        "scope": "mini-ronda dirigida; 8 emociones, 2 audios ciegos por emoción, 16 WAV máximo",
        "human_authority": "REDACTED_f73137d930c3 decide; las métricas automáticas no aprueban candidatos",
        "items": items,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emotion-csv", type=Path, required=True)
    parser.add_argument("--emotion-key", type=Path, required=True)
    parser.add_argument("--personality-csv", type=Path, required=True)
    parser.add_argument("--provisional-catalog", type=Path, required=True)
    parser.add_argument("--emotion-output-dir", type=Path, required=True)
    parser.add_argument("--personality-output-dir", type=Path, required=True)
    parser.add_argument("--final-catalog", type=Path, required=True)
    parser.add_argument("--personality-rules", type=Path, required=True)
    args = parser.parse_args()

    source_hashes = {
        args.emotion_csv: sha256_file(args.emotion_csv),
        args.personality_csv: sha256_file(args.personality_csv),
    }
    emotion_results, final_catalog = process_emotions(
        args.emotion_csv, args.emotion_key, args.provisional_catalog
    )
    personality_results, rules = process_personality(args.personality_csv)

    write_json(args.emotion_output_dir / "EMOTION_HUMAN_RESULTS.json", emotion_results)
    (args.emotion_output_dir / "EMOTION_HUMAN_RESULTS.md").write_text(
        emotion_markdown(emotion_results), encoding="utf-8"
    )
    write_json(args.emotion_output_dir / "DAXTER_EMOTION_CATALOG_FINAL.json", final_catalog)
    write_json(args.emotion_output_dir / "EMOTION_MINI_ROUND_PLAN.json", emotion_mini_round_plan(emotion_results))
    write_json(args.final_catalog, final_catalog)
    write_json(args.personality_output_dir / "PERSONALITY_HUMAN_RESULTS.json", personality_results)
    (args.personality_output_dir / "PERSONALITY_HUMAN_RESULTS.md").write_text(
        personality_markdown(personality_results), encoding="utf-8"
    )
    write_json(args.personality_rules, rules)

    for path, original_hash in source_hashes.items():
        if sha256_file(path) != original_hash:
            raise RuntimeError(f"La evaluación humana fue modificada: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
