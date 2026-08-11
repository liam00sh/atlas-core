"""Resuelve la evaluación humana ciega de Ronda B sin modificar sus fuentes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


SCORE_FIELDS = (
    "naturalidad_1_5",
    "inteligibilidad_1_5",
    "similitud_daxter_1_5",
    "emocion_1_5",
    "pronunciacion_1_5",
    "espanol_espana_1_5",
    "inicio_sin_cortes_1_5",
    "estabilidad_1_5",
    "artefactos_1_5",
)
CANDIDATES = ("B0", "B1", "B2", "B3")
NORMALIZATION_CASES = {
    "Jak→Yak": ("corrected", ("05_emocionado", "11_jugueton", "16_jak_espera")),
    "Atlas→Átlas": (
        "corrected",
        ("01_neutral", "08_curioso", "12_numeros_nombres", "13_larga", "14_atlas", "18_oye_atlas", "20_tecnica"),
    ),
    "Home Assistant→Joum Asístent": ("corrected", ("20_tecnica",)),
    "Telegram→Télegram": ("corrected", ("20_tecnica",)),
    "verbalización de fechas y números": ("original", ("12_numeros_nombres",)),
}
NOTE_THEMES = {
    "acento_es": re.compile(r"latino|méxic|mejican|españ|acento", re.I),
    "inicio_cortado": re.compile(r"cort|principio|inicio|empieza", re.I),
    "pronunciacion_nombres": re.compile(r"pronunci|palabra|nombre|atlas|daxter|jak|telegram|assistant", re.I),
    "artefactos_o_ininteligible": re.compile(r"artefact|robot|ruido|raro|extrañ|idioma|inentend|inintelig|repet", re.I),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs(csv_path: Path, key_path: Path) -> tuple[list[dict], str, str]:
    csv_hash = sha256_file(csv_path)
    key_hash = sha256_file(key_path)
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    key_payload = json.loads(key_path.read_text(encoding="utf-8-sig"))
    entries = key_payload["entries"] if isinstance(key_payload, dict) else key_payload
    key_by_code = {entry["blind_code"]: entry for entry in entries}
    if len(rows) != 136 or len(entries) != 136 or len(key_by_code) != 136:
        raise ValueError("La evaluación y la clave deben contener exactamente 136 entradas únicas")
    if {row["blind_code"] for row in rows} != set(key_by_code):
        raise ValueError("Los blind_code del CSV y BLIND_KEY no forman una biyección")

    joined = []
    for row in rows:
        entry = key_by_code[row["blind_code"]]
        if row["battery"] != entry["battery"] or row["case_id"] != entry["case_id"]:
            raise ValueError(f"Clave incoherente para {row['blind_code']}")
        parsed = dict(row)
        parsed.update(entry)
        for field in SCORE_FIELDS:
            try:
                parsed[field] = float(row[field])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Puntuación ausente o inválida en {row['blind_code']}/{field}") from error
            if not 1 <= parsed[field] <= 5:
                raise ValueError(f"Puntuación fuera de 1–5 en {row['blind_code']}/{field}")
        joined.append(parsed)
    return joined, csv_hash, key_hash


def aggregate(rows: list[dict]) -> dict:
    result: dict[str, dict] = {}
    for candidate in CANDIDATES:
        result[candidate] = {}
        for battery in ("corrected", "original", "global"):
            subset = [row for row in rows if row["candidate"] == candidate and (battery == "global" or row["battery"] == battery)]
            means = {field: round(statistics.mean(row[field] for row in subset), 4) for field in SCORE_FIELDS}
            preferences = Counter((row.get("preferencia") or "").strip().casefold() for row in subset)
            result[candidate][battery] = {
                "samples": len(subset),
                "means": means,
                "global_mean": round(statistics.mean(means.values()), 4),
                "preferences": {
                    "si": preferences.get("si", 0),
                    "no": preferences.get("no", 0),
                    "empate": preferences.get("empate", 0),
                    "sin_respuesta": preferences.get("", 0),
                },
            }
    return result


def normalization_evidence(rows: list[dict]) -> dict:
    evidence = {}
    for name, (battery, case_ids) in NORMALIZATION_CASES.items():
        candidates = {}
        for candidate in ("B0", "B1"):
            subset = [
                row for row in rows
                if row["candidate"] == candidate and row["battery"] == battery and row["case_id"] in case_ids
            ]
            candidates[candidate] = {
                field: round(statistics.mean(row[field] for row in subset), 4) for field in SCORE_FIELDS
            }
        evidence[name] = {"battery": battery, "case_ids": list(case_ids), "human_means": candidates}
    return evidence


def analyze_notes(rows: list[dict]) -> dict:
    result = {}
    for candidate in CANDIDATES:
        subset = [row for row in rows if row["candidate"] == candidate]
        result[candidate] = {
            "notes_analyzed": len(subset),
            "theme_mentions": {
                theme: sum(bool(pattern.search(row.get("notas", ""))) for row in subset)
                for theme, pattern in NOTE_THEMES.items()
            },
            "representative_blind_codes": {
                theme: [row["blind_code"] for row in subset if pattern.search(row.get("notas", ""))][:5]
                for theme, pattern in NOTE_THEMES.items()
            },
        }
    return result


def decide(human: dict, automatic: dict, norm_evidence: dict) -> dict:
    corrected = {candidate: human[candidate]["corrected"] for candidate in CANDIDATES}
    winner = max(CANDIDATES, key=lambda candidate: (
        corrected[candidate]["means"]["similitud_daxter_1_5"],
        corrected[candidate]["global_mean"],
        corrected[candidate]["means"]["pronunciacion_1_5"],
        corrected[candidate]["means"]["inicio_sin_cortes_1_5"],
    ))
    runner_up = max((candidate for candidate in CANDIDATES if candidate != winner), key=lambda candidate: (
        human[candidate]["global"]["means"]["similitud_daxter_1_5"],
        human[candidate]["global"]["global_mean"],
    ))
    clear = (
        winner == "B1"
        and corrected[winner]["means"]["similitud_daxter_1_5"] == max(
            item["means"]["similitud_daxter_1_5"] for item in corrected.values()
        )
        and corrected[winner]["global_mean"] == max(item["global_mean"] for item in corrected.values())
        and automatic["candidates"][winner]["corrected"]["automatic_anomalies"] == 0
    )
    if not clear:
        return {
            "winner": None,
            "runner_up": None,
            "requires_mini_round": True,
            "required_comparison": "Comparar los candidatos empatados en similitud con casos de nombres, español de España e inicios.",
        }

    accepted = [
        {
            "rule": "Jak→Yak",
            "reason": "En sus tres casos corregidos B1 mejora similitud, pronunciación, naturalidad, emoción e inicios frente a B0.",
            "evidence": norm_evidence["Jak→Yak"],
        },
        {
            "rule": "verbalización de fechas y números",
            "reason": "En el caso original de números sube inteligibilidad 2→4, pronunciación 1→4 y español de España 1→4.",
            "evidence": norm_evidence["verbalización de fechas y números"],
        },
    ]
    rejected = [
        {
            "rule": "Atlas→Átlas",
            "reason": "Aunque la similitud agregada sube ligeramente, empeoran pronunciación 4,4286→4,1429 y español de España 4,0000→3,5714; el Atlas aislado de B0 fue 5/5 en todo.",
            "evidence": norm_evidence["Atlas→Átlas"],
        },
        {
            "rule": "Home Assistant→Joum Asístent",
            "reason": "El único caso técnico mantiene pronunciación 3/5 y reduce similitud 4→3; las notas indican pronunciación incorrecta.",
            "evidence": norm_evidence["Home Assistant→Joum Asístent"],
        },
        {
            "rule": "Telegram→Télegram",
            "reason": "No aporta una mejora separable en el único caso técnico y comparte el descenso de similitud; se conserva la grafía original.",
            "evidence": norm_evidence["Telegram→Télegram"],
        },
        {
            "rule": "Daxter→Dákster",
            "reason": "La batería no contiene una comparación directa que aísle esta sustitución; queda rechazada por falta de evidencia humana.",
            "evidence": None,
        },
    ]
    return {
        "winner": winner,
        "runner_up": runner_up,
        "requires_mini_round": False,
        "reasoning": [
            "B1 obtiene la mejor similitud humana corregida (4,2381/5) y la mejor media corregida (4,4815/5).",
            "En global B1 alcanza 4,4347/5 y empata con B0 en similitud Daxter (4,0882/5).",
            "B1 mejora pronunciación, español de España e inicios frente a B0 y no presenta anomalías automáticas en la batería corregida.",
            "B0 queda segundo porque conserva mejor naturalidad/emoción original y el mayor ECAPA original, pero tiene más cortes y peor rendimiento operativo corregido.",
        ],
        "human_metrics": human,
        "automatic_metrics": automatic["candidates"],
        "known_weaknesses": [
            "Acento latinoamericano todavía perceptible en numerosas notas.",
            "Naturalidad y emoción de B1 original quedan por debajo de B0.",
            "Atlas, Home Assistant y Telegram no admiten las grafías fonéticas probadas.",
            "Las frases técnicas y largas todavía pueden sonar rápidas o presentar artefactos.",
        ],
        "accepted_inference_normalizations": accepted,
        "rejected_inference_normalizations": rejected,
    }


def markdown_report(payload: dict) -> str:
    lines = [
        "# Resultados humanos de Ronda B",
        "",
        f"Fuente humana inmutable: `{payload['source']['human_csv']}` (`{payload['source']['human_csv_sha256']}`).",
        "",
        "Las nueve métricas están completas en las 136 muestras. La similitud con Daxter es prioritaria; ECAPA sólo sirve como contraste automático.",
        "",
        "| Candidato | Batería | Media | Similitud | Español ES | Pronunciación | Inicio | SI/NO/Empate |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for candidate in CANDIDATES:
        for battery in ("corrected", "original", "global"):
            item = payload["human_metrics"][candidate][battery]
            means = item["means"]
            pref = item["preferences"]
            lines.append(
                f"| {candidate} | {battery} | {item['global_mean']:.4f} | {means['similitud_daxter_1_5']:.4f} | "
                f"{means['espanol_espana_1_5']:.4f} | {means['pronunciacion_1_5']:.4f} | "
                f"{means['inicio_sin_cortes_1_5']:.4f} | {pref['si']}/{pref['no']}/{pref['empate']} |"
            )
    decision = payload["decision"]
    lines.extend(["", "## Decisión", "", f"Ganador: **{decision['winner']}**. Segundo: **{decision['runner_up']}**.", ""])
    lines.extend(f"- {reason}" for reason in decision["reasoning"])
    lines.extend(["", "## Normalizaciones", "", "Aceptadas:"])
    lines.extend(f"- {item['rule']}: {item['reason']}" for item in decision["accepted_inference_normalizations"])
    lines.extend(["", "Rechazadas:"])
    lines.extend(f"- {item['rule']}: {item['reason']}" for item in decision["rejected_inference_normalizations"])
    lines.extend(["", "## Notas humanas", ""])
    for candidate in CANDIDATES:
        themes = payload["note_analysis"][candidate]["theme_mentions"]
        lines.append(f"- {candidate}: acento {themes['acento_es']}; inicios/cortes {themes['inicio_cortado']}; pronunciación/nombres {themes['pronunciacion_nombres']}; artefactos {themes['artefactos_o_ininteligible']}.")
    return "\n".join(lines) + "\n"


def winner_profile(decision: dict, source: dict) -> dict:
    return {
        "profile_id": "daxter_es_jak2",
        "version": "1.0.0",
        "status": "round_b_human_winner_emotion_validation_pending",
        "model": {"package": "chatterbox-tts", "version": "0.1.7", "architecture": "Chatterbox Multilingual V2"},
        "winner": decision["winner"],
        "reference_strategy": "jak2_diverse",
        "reference_file": "voice_lab_round_b/references/reference_daxter_jak2_diverse.wav",
        "language_id": "es",
        "parameters": {"cfg_weight": 0.35, "temperature": 0.8, "repetition_penalty": 2.0, "min_p": 0.05, "top_p": 1.0},
        "exaggeration_policy": {"neutral_or_confident": 0.45, "expressive": 0.65},
        "accepted_inference_normalizations": ["Jak→Yak", "verbalización de fechas y números"],
        "rejected_inference_normalizations": ["Atlas→Átlas", "Daxter→Dákster", "Home Assistant→Joum Asístent", "Telegram→Télegram"],
        "seed_policy": "sha256(base_seed,candidate,battery,case_id); base_seed=20260809",
        "provenance": {
            "human_csv_sha256": source["human_csv_sha256"],
            "blind_key_sha256": source["blind_key_sha256"],
            "decision_file": "voice_lab_round_b/ROUND_B_FINAL_DECISION.json",
            "official_chatterbox_commit": "5de7a54aa4e5e2baadb0182dde554908b48b85c2",
            "fine_tuning": "not_performed_no_official_stable_pipeline",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-csv", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--automatic-metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile-output", type=Path, required=True)
    args = parser.parse_args()
    rows, csv_hash, key_hash = load_inputs(args.human_csv.resolve(), args.blind_key.resolve())
    automatic = json.loads(args.automatic_metrics.read_text(encoding="utf-8-sig"))
    human = aggregate(rows)
    norm = normalization_evidence(rows)
    source = {
        "human_csv": args.human_csv.name,
        "human_csv_sha256": csv_hash,
        "blind_key": args.blind_key.name,
        "blind_key_sha256": key_hash,
        "rows": len(rows),
    }
    decision = decide(human, automatic, norm)
    if decision.get("winner") is None:
        raise SystemExit("La evaluación no produce un ganador claro; se requiere mini-ronda")
    payload = {
        "source": source,
        "human_metrics": human,
        "normalization_evidence": norm,
        "note_analysis": analyze_notes(rows),
        "decision": decision,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "ROUND_B_HUMAN_RESULTS.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "ROUND_B_HUMAN_RESULTS.md").write_text(markdown_report(payload), encoding="utf-8")
    (args.output_dir / "ROUND_B_FINAL_DECISION.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.profile_output.parent.mkdir(parents=True, exist_ok=True)
    args.profile_output.write_text(json.dumps(winner_profile(decision, source), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"winner": decision["winner"], "runner_up": decision["runner_up"], "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
