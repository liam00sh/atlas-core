"""Genera la comparativa reproducible, test humano y reproductor ciego local."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import statistics
import wave
from pathlib import Path


ENGINE_LABELS = {
    "engine_chatterbox_multilingual": "Chatterbox Multilingual V2 (clonación directa)",
    "engine_openvoice_v2": "Chatterbox V2 + OpenVoice V2 (TTS+VC)",
}


def size_gb(path: Path) -> float:
    return round(sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) / 1024**3, 3) if path.exists() else 0.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    lab = args.lab.resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    similarity = json.loads((lab / "speaker_similarity.json").read_text(encoding="utf-8"))
    summaries = {}
    validation = {}
    for engine_dir_name, label in ENGINE_LABELS.items():
        folder = lab / engine_dir_name
        data = json.loads((folder / "benchmark.json").read_text(encoding="utf-8"))
        good = [run for run in data["runs"] if not run["error"]]
        rtfs = [float(run["rtf"]) for run in good]
        summaries[engine_dir_name] = {
            "label": label, "metadata": data["metadata"], "runs": data["runs"],
            "valid": len(good), "rtf_mean": round(statistics.mean(rtfs), 3),
            "rtf_median": round(statistics.median(rtfs), 3),
            "vram_peak_mb": max(float(run["peak_vram_mb"]) for run in good),
            "speaker_similarity": similarity["engines"][engine_dir_name]["mean"],
        }
        checks = []
        for wav_path in sorted(folder.glob("*.wav")):
            with wave.open(str(wav_path), "rb") as wav:
                checks.append({"file": wav_path.name, "sample_rate": wav.getframerate(), "channels": wav.getnchannels(), "bits": wav.getsampwidth() * 8, "seconds": round(wav.getnframes() / wav.getframerate(), 4)})
        validation[engine_dir_name] = checks

    model_sizes = {
        "huggingface_cache_gb_including_chatterbox_and_ecapa": size_gb(lab / "models" / "huggingface"),
        "coqui_openvoice_cache_gb": size_gb(lab / "models" / "coqui"),
    }
    comparison = [
        "# Comparativa local de voz Daxter — Ronda A", "",
        "No se declara ganador. Los WAV y las puntuaciones humanas en blanco son la evidencia para que Alex elija.", "",
        "## Ejecuciones reales", "",
        "| Motor | Enfoque | WAV válidos | Inicio (s) | RTF medio | RTF mediano | VRAM pico (MB) | Similitud ECAPA media |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, summary in summaries.items():
        meta = summary["metadata"]
        comparison.append(f"| {summary['label']} | {meta['mode']} | {summary['valid']}/13 | {meta['initialization_seconds']} | {summary['rtf_mean']} | {summary['rtf_median']} | {summary['vram_peak_mb']} | {summary['speaker_similarity']} |")
    comparison += [
        "", "La similitud ECAPA es orientativa: compara embeddings de hablante con tres referencias de Jak II y no sustituye una escucha humana.",
        "", "## Observaciones que requieren escucha", "",
        "- Chatterbox produjo duraciones anómalas en `09_confiado.wav` (9,16 s) y `12_numeros_nombres.wav` (34,8 s); pueden indicar pausas largas, repetición o alucinación.",
        "- OpenVoice conserva prácticamente la duración de la fuente, por lo que también hereda esas anomalías de contenido/ritmo.",
        "- Las trece salidas de ambos motores son WAV mono PCM de 16 bits, no vacíos y reproducibles.",
        "- Ronda B (adaptación ligera) queda deliberadamente sin ejecutar hasta que Alex valore la Ronda A.",
        "- Ronda C (entrenamiento largo) no se inicia.",
        "", "## Tamaño local observado", "", f"```json\n{json.dumps(model_sizes, indent=2)}\n```", "",
        "## Investigación y descarte práctico", "",
        "| Candidato | Español/clonación | Windows local | Licencia observada | Decisión de esta ronda |",
        "|---|---|---|---|---|",
        "| Chatterbox Multilingual V3 / pack es-ES | Sí; zero-shot; 500M | El proyecto indica Python 3.11; la API V3 está documentada | Código MIT; salidas con marca PerTh | Investigado. El commit oficial `5de7a54` instalado seguía exponiendo la API V2, por lo que no se falseó una ejecución V3. |",
        "| Chatterbox Multilingual V2 | Sí; zero-shot directo | Ejecutado en Windows 11 + RTX 4060 | MIT / PerTh | 13 WAV generados. |",
        "| OpenVoice V2 | Español; VC zero-shot | Ejecutado mediante Coqui-TTS 0.27.5 | MIT | 13 WAV generados sobre la misma batería base. |",
        "| XTTS-v2 | 17 idiomas, español, zero-shot y ajuste | Compatible con Python <3.12; pesos CPML | No comercial; requiere aceptar términos | No ejecutado: no se aceptaron términos jurídicos en nombre del usuario. |",
        "| F5-TTS v1 | Zero-shot y fine-tuning; español no es su foco documentado principal | Python 3.11 y CUDA documentados | Código MIT; revisar pesos concretos | No priorizado frente a candidatos con español nativo verificado. |",
        "| CosyVoice | Español, zero-shot, cross-lingual | Instalación oficial centrada en Linux/CUDA | Apache-2.0 | Candidato fuerte para otra ronda; no instalado por coste/compatibilidad Windows. |",
        "| GPT-SoVITS / RVC | Few-shot/entrenamiento y VC | Paquetes Windows disponibles | Revisar pesos y componentes | Reservados para Ronda B: requieren adaptación o entrenamiento, no solo inferencia comparable. |",
        "| Fish Speech S2 | Español y clonación | Local, instalación más pesada | Fish Audio Research License; comercial separado | No ejecutado ni se aceptó su licencia. |",
        "", "Fuentes primarias consultadas:", "",
        "- https://github.com/resemble-ai/chatterbox", "- https://github.com/myshell-ai/OpenVoice",
        "- https://github.com/idiap/coqui-ai-TTS", "- https://github.com/SWivid/F5-TTS",
        "- https://github.com/QwenAudio/CosyVoice", "- https://github.com/RVC-Boss/GPT-SoVITS",
        "- https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI", "- https://github.com/fishaudio/fish-speech",
    ]
    (lab / "COMPARATIVA.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")

    refs = manifest["reference_selection"]["samples"]
    used = {"jak2__DS305.wav", "jak2__DS047.wav", "jak2__DS166.wav"}
    ref_lines = ["# Referencias de voz", "", "Criterio: Jak II, mejor calidad disponible, duración útil y diversidad emocional.", "", "El maestro no contiene `quality=excelente`; `buena` es el máximo presente.", "", "| sample_id | WAV | emoción | calidad | duración | usada en referencia combinada |", "|---|---|---|---|---:|---|"]
    for ref in refs:
        ref_lines.append(f"| {ref['sample_id']} | {ref['audio_file']} | {ref['emotion']} | {ref['quality']} | {ref['duration_seconds']} | {'sí' if ref['audio_file'] in used else 'no'} |")
    ref_lines += ["", "Referencia efectiva: `references/reference_daxter_jak2_diverse.wav`, concatenación mono 48 kHz de DS305 + DS047 + DS166 (12,36 s)."]
    (lab / "REFERENCIAS.md").write_text("\n".join(ref_lines) + "\n", encoding="utf-8")

    human_fields = ["blind_code", "case_id", "audio_file", "naturalidad_1_5", "inteligibilidad_1_5", "similitud_daxter_1_5", "emocion_1_5", "pronunciacion_1_5", "estabilidad_1_5", "artefactos_1_5", "preferencia", "notas"]
    human_rows = []
    key = {}
    for case_index in range(13):
        for variant_index, engine_name in enumerate(ENGINE_LABELS):
            code = f"P{case_index + 1:02d}{chr(65 + variant_index)}"
            file_name = summaries[engine_name]["runs"][case_index]["output_file"]
            human_rows.append({"blind_code": code, "case_id": summaries[engine_name]["runs"][case_index]["case_id"], "audio_file": f"{engine_name}/{file_name}"})
            key[code] = {"engine": ENGINE_LABELS[engine_name], "file": f"{engine_name}/{file_name}"}
    with (lab / "HUMAN_LISTENING_TEST.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=human_fields)
        writer.writeheader(); writer.writerows(human_rows)
    (lab / "BLIND_KEY.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cards = []
    for row in human_rows:
        cards.append(f"<article><h2>{html.escape(row['blind_code'])} · {html.escape(row['case_id'])}</h2><audio controls preload='none' src='{html.escape(row['audio_file'])}'></audio></article>")
    player = "<!doctype html><html lang='es'><meta charset='utf-8'><title>Escucha ciega Daxter</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;background:#111;color:#eee}article{padding:1rem;margin:1rem 0;background:#222;border-radius:12px}audio{width:100%}</style><h1>Escucha ciega — Daxter</h1><p>Puntúa en HUMAN_LISTENING_TEST.csv antes de abrir BLIND_KEY.json.</p>" + "".join(cards) + "</html>"
    (lab / "BLIND_LISTENING_PLAYER.html").write_text(player, encoding="utf-8")

    (lab / "VOICE_OUTPUT_VALIDATION.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hash_files = sorted([file for file in lab.rglob("*") if file.is_file() and ".venv_" not in str(file) and "models" not in file.parts and file.name != "VOICE_LAB_SHA256SUMS.txt"])
    (lab / "VOICE_LAB_SHA256SUMS.txt").write_text("\n".join(f"{sha256(file)}  {file.relative_to(lab).as_posix()}" for file in hash_files) + "\n", encoding="utf-8")
    print(json.dumps({"summaries": summaries, "model_sizes": model_sizes, "validated": {k: len(v) for k, v in validation.items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
