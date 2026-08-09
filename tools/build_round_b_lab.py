"""Valida Ronda B y construye comparación, reproductor y CSV ciegos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import shutil
import statistics
import wave
from collections import Counter, defaultdict
from pathlib import Path

from tools.round_b_battery import CANDIDATES


SCORE_FIELDS = (
    "naturalidad_1_5", "inteligibilidad_1_5", "similitud_daxter_1_5", "emocion_1_5",
    "pronunciacion_1_5", "espanol_espana_1_5", "inicio_sin_cortes_1_5",
    "estabilidad_1_5", "artefactos_1_5", "preferencia", "notas",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def round_a_summary(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {"source_file": path.name, "source_sha256": sha256_file(path), "engines": {}}
    metrics = ("naturalidad_1_5", "inteligibilidad_1_5", "similitud_daxter_1_5", "emocion_1_5", "pronunciacion_1_5", "estabilidad_1_5", "artefactos_1_5")
    for label, marker in (("chatterbox", "engine_chatterbox_multilingual"), ("openvoice", "engine_openvoice_v2")):
        subset = [row for row in rows if marker in row["audio_file"]]
        means = {metric: round(statistics.mean(float(row[metric]) for row in subset), 4) for metric in metrics}
        result["engines"][label] = {
            "samples": len(subset), "metrics": means, "global_mean": round(statistics.mean(means.values()), 4),
            "preferences": dict(Counter(row["preferencia"].strip().casefold() for row in subset)),
        }
    result["decision"] = "Chatterbox Multilingual V2 seleccionado; similitud humana prioritaria."
    return result


def validate_wav(path: Path) -> dict:
    with wave.open(str(path), "rb") as handle:
        return {
            "sample_rate": handle.getframerate(), "channels": handle.getnchannels(),
            "bits": handle.getsampwidth() * 8, "seconds": round(handle.getnframes() / handle.getframerate(), 4),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-dir", type=Path, required=True)
    parser.add_argument("--round-a-human-csv", type=Path, required=True)
    parser.add_argument("--similarity", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260809)
    args = parser.parse_args()
    lab = args.lab_dir.resolve()
    blind_audio = lab / "blind_audio"
    blind_audio.mkdir(parents=True, exist_ok=True)
    similarity = json.loads(args.similarity.read_text(encoding="utf-8"))
    run_manifest = json.loads((lab / "ROUND_B_RUN_MANIFEST.json").read_text(encoding="utf-8"))
    round_a = round_a_summary(args.round_a_human_csv.resolve())
    (lab / "ROUND_A_HUMAN_EVALUATION_SUMMARY.json").write_text(json.dumps(round_a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summaries = {}
    entries = []
    anomalies = []
    for candidate in CANDIDATES:
        summaries[candidate] = {}
        for battery_name, expected in (("original", 13), ("corrected", 21)):
            folder = lab / f"candidate_{candidate}" / f"benchmark_{battery_name}"
            data = json.loads((folder / "benchmark.json").read_text(encoding="utf-8"))
            rows = data["runs"]
            if len(rows) != expected or any(row["error"] for row in rows):
                raise SystemExit(f"{candidate}/{battery_name} no tiene {expected} ejecuciones válidas")
            for row in rows:
                path = folder / row["output_file"]
                wav = validate_wav(path)
                if wav["channels"] != 1 or wav["bits"] != 16:
                    raise SystemExit(f"Formato WAV inesperado: {path}")
                if row["automatic_flags"]:
                    anomalies.append({"candidate": candidate, "battery": battery_name, "case_id": row["case_id"], "flags": row["automatic_flags"], "seconds": row["audio_seconds"]})
                entries.append({"candidate": candidate, "battery": battery_name, "case_id": row["case_id"], "source": path, "requested_text": row["requested_text"]})
            rtfs = [float(row["rtf"]) for row in rows]
            summaries[candidate][battery_name] = {
                "wav": len(rows), "rtf_mean": round(statistics.mean(rtfs), 4),
                "rtf_median": round(statistics.median(rtfs), 4),
                "vram_peak_mb": max(float(row["peak_vram_mb"]) for row in rows),
                "generation_seconds": round(sum(float(row["generation_seconds"]) for row in rows), 4),
                "duration_seconds": round(sum(float(row["audio_seconds"]) for row in rows), 4),
                "ecapa_mean": similarity["candidates"][candidate][battery_name]["mean"],
                "automatic_anomalies": sum(bool(row["automatic_flags"]) for row in rows),
            }

    rng = random.Random(args.seed)
    rng.shuffle(entries)
    blind_rows = []
    key = []
    for index, entry in enumerate(entries, 1):
        code = f"RB{index:04d}"
        filename = f"{code}.wav"
        shutil.copy2(entry["source"], blind_audio / filename)
        blind_rows.append({
            "blind_code": code, "battery": entry["battery"], "case_id": entry["case_id"],
            "audio_file": f"blind_audio/{filename}", **{field: "" for field in SCORE_FIELDS},
        })
        key.append({
            "blind_code": code, "candidate": entry["candidate"], "battery": entry["battery"],
            "case_id": entry["case_id"], "source_file": entry["source"].relative_to(lab).as_posix(),
            "blind_file": f"blind_audio/{filename}", "requested_text": entry["requested_text"],
        })
    blind_rows.sort(key=lambda row: (row["battery"], row["case_id"], row["blind_code"]))
    fields = ("blind_code", "battery", "case_id", "audio_file") + SCORE_FIELDS
    human_csv = lab / "HUMAN_LISTENING_TEST_ROUND_B.csv"
    if human_csv.exists() and any(row.get("naturalidad_1_5") for row in csv.DictReader(human_csv.open(encoding="utf-8-sig"))):
        raise SystemExit("El CSV humano ya contiene puntuaciones; no se sobrescribe")
    with human_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(blind_rows)
    (lab / "BLIND_KEY.json").write_text(json.dumps({"seed": args.seed, "entries": key}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    grouped = defaultdict(list)
    for row in blind_rows:
        grouped[(row["battery"], row["case_id"])].append(row)
    sections = []
    for (battery_name, case_id), rows in sorted(grouped.items()):
        cards = "".join(
            f'<article class="card"><strong>{html.escape(row["blind_code"])}</strong><audio controls preload="none" src="{html.escape(row["audio_file"])}"></audio></article>'
            for row in rows
        )
        sections.append(f'<section data-battery="{battery_name}"><h2>{html.escape(battery_name)} · {html.escape(case_id)}</h2><div class="grid">{cards}</div></section>')
    player = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ronda B — escucha ciega Daxter</title><style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:auto;padding:24px;background:#10131a;color:#f4f6fa}}
.notice{{background:#202838;border-left:4px solid #ff9f43;padding:14px}} select{{padding:8px;margin:12px 0}}
section{{border-top:1px solid #394257;padding:16px 0}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.card{{background:#1b2130;padding:12px;border-radius:8px}} audio{{display:block;width:100%;margin-top:8px}} code{{color:#ffcf70}}
</style></head><body><h1>Ronda B — escucha ciega de Daxter</h1>
<p class="notice">La identidad de las cuatro configuraciones está oculta. Puntúa siempre con <strong>5 = mejor</strong>. La métrica prioritaria es similitud con Daxter; revisa también español de España, inicio sin cortes, Jak, Atlas, números, frases largas, risa y emoción.</p>
<label>Batería: <select id="filter"><option value="all">Todas</option><option value="corrected">Corregida y pruebas objetivo</option><option value="original">Original histórica</option></select></label>
{''.join(sections)}<script>
document.getElementById('filter').addEventListener('change',e=>{{document.querySelectorAll('section').forEach(s=>s.hidden=e.target.value!=='all'&&s.dataset.battery!==e.target.value)}})
</script></body></html>"""
    (lab / "BLIND_LISTENING_PLAYER.html").write_text(player, encoding="utf-8")

    comparison = [
        "# Comparativa Ronda B — Chatterbox Multilingual V2", "",
        "No se declara ganador de Ronda B. REDACTED_2c7b6821719d debe decidir después de la escucha ciega.", "",
        "## Decisión humana de Ronda A", "",
        f"- Chatterbox: media {round_a['engines']['chatterbox']['global_mean']}; similitud Daxter {round_a['engines']['chatterbox']['metrics']['similitud_daxter_1_5']}.",
        f"- OpenVoice: media {round_a['engines']['openvoice']['global_mean']}; similitud Daxter {round_a['engines']['openvoice']['metrics']['similitud_daxter_1_5']}.",
        "- Motor base seleccionado: Chatterbox Multilingual V2. OpenVoice queda como alternativa experimental documentada.", "",
        "## Límite de adaptación", "",
        "El commit oficial `5de7a54aa4e5e2baadb0182dde554908b48b85c2` no contiene scripts ni API pública de entrenamiento/fine-tuning. B1–B3 son configuraciones de conditioning e inferencia, no checkpoints entrenados.",
        "La API V2 instalada sólo expone idioma `es`, referencia, exaggeration, CFG, temperatura y muestreo; no ofrece locale `es-ES`, diccionario fonético ni phonemizer configurable.",
        "Fuentes: https://github.com/resemble-ai/chatterbox y https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/mtl_tts.py", "",
        "## Entorno, licencia y coste observado", "",
        f"- GPU: {run_manifest['gpu']}; CUDA {run_manifest['cuda']}; PyTorch {run_manifest['torch']}.",
        f"- Inicialización: {run_manifest['initialization_seconds']} s; RAM del proceso: {run_manifest['ram_before_mb']}→{run_manifest['ram_after_mb']} MB.",
        "- Código Chatterbox: MIT. Las salidas incorporan la marca de agua PerTh del proyecto oficial.",
        "- Riesgos: acento no controlable por locale, grafías fonéticas experimentales, alucinación/repetición estocástica y ausencia de soporte oficial de entrenamiento.", "",
        "## Candidatos", "", "| Candidato | Configuración | Batería | WAV | RTF medio | VRAM pico MB | ECAPA media | Avisos automáticos |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for candidate, config in CANDIDATES.items():
        for battery_name in ("original", "corrected"):
            value = summaries[candidate][battery_name]
            comparison.append(f"| {candidate} | {config['label']} | {battery_name} | {value['wav']} | {value['rtf_mean']} | {value['vram_peak_mb']} | {value['ecapa_mean']} | {value['automatic_anomalies']} |")
    comparison += ["", "Tiempos acumulados de generación (sin inicialización):"]
    for candidate in CANDIDATES:
        comparison.append(f"- {candidate}: original {summaries[candidate]['original']['generation_seconds']} s; corregida {summaries[candidate]['corrected']['generation_seconds']} s.")
    comparison += ["", "ECAPA sólo aproxima identidad de hablante. No mide acento, pronunciación, emoción o naturalidad.", "", "## Avisos que requieren escucha", ""]
    for item in anomalies:
        comparison.append(f"- {item['candidate']}/{item['battery']}/{item['case_id']}: `{item['flags']}` ({item['seconds']} s).")
    comparison += [
        "", "## Diccionario de inferencia", "",
        "B1–B3 prueban, sin modificar el metadata: Jak→Yak, Atlas→Átlas, Daxter→Dákster, Home Assistant→Joum Asístent y Telegram→Télegram; números/fecha conocidos se escriben con palabras.",
        "Estas grafías son hipótesis acústicas y deben aceptarse o rechazarse por escucha.", "",
        "## Recursos", "", "- `BLIND_LISTENING_PLAYER.html`", "- `HUMAN_LISTENING_TEST_ROUND_B.csv`", "- `BLIND_KEY.json`", "- `speaker_similarity_round_b.json`", "",
    ]
    (lab / "COMPARATIVA_RONDA_B.md").write_text("\n".join(comparison), encoding="utf-8")
    validation = {"candidates": summaries, "anomalies": anomalies, "blind_entries": len(blind_rows), "winner": None}
    (lab / "ROUND_B_VALIDATION.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hash_file = lab / "ROUND_B_SHA256SUMS.txt"
    targets = sorted(path for path in lab.rglob("*") if path.is_file() and path != hash_file)
    hash_file.write_text("".join(f"{sha256_file(path)}  {path.relative_to(lab).as_posix()}\n" for path in targets), encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
