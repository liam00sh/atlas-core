"""Batería STT humana reanudable; inspecciona rutas sin ejecutar acciones."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_stt_conversation_battery import write_reports
from voice.microphone import ManualMicrophoneRecorder
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService
from voice.text_normalizer import ContextualTranscriptNormalizer


@dataclass(frozen=True)
class RouterObservation:
    intent: str
    entity: str = ""
    command: bool = False
    safe_action: bool = False
    confirmation_required: bool = False


def choose_microphone(recorder: ManualMicrophoneRecorder, *, input_func=input) -> str:
    """Selecciona un dispositivo sin cargar Atlas ni sus ejecutores."""
    if recorder.device_name:
        return recorder.device_name
    devices = recorder.list_devices()
    if not devices:
        return recorder.selected_device()
    if len(devices) == 1:
        recorder.device_name = devices[0]
        return devices[0]
    print("Micrófonos detectados:")
    for index, device in enumerate(devices, 1):
        print(f"  {index}. {device}")
    while True:
        selected = input_func("Elige el número del micrófono: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(devices):
            recorder.device_name = devices[int(selected) - 1]
            return recorder.device_name
        print("Selección no válida.")


def plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in value if not unicodedata.combining(char)).strip()


def inspect_router_only(text: str) -> RouterObservation:
    """Contrato diagnóstico puro: no importa Atlas, adaptadores ni ejecutores."""
    value = plain(text)
    suffix = re.sub(r"\s+(?:por favor|ahora)$", "", value)
    if "luz del acuario pequeno" in value:
        if value.startswith(("enciende", "encender")):
            return RouterObservation("home.turn_on", "luz del acuario pequeño", True, True)
        if value.startswith(("apaga", "apagar")):
            return RouterObservation("home.turn_off", "luz del acuario pequeño", True, True)
        return RouterObservation("home.state", "luz del acuario pequeño")
    if "home assistant" in value:
        return RouterObservation("infrastructure.status", "Home Assistant")
    if "docker" in value or "telegram esta" in value or "ollama" in value:
        entity = "Docker" if "docker" in value else ("Telegram" if "telegram" in value else "Ollama")
        return RouterObservation("infrastructure.status", entity)
    if value.startswith("reinicia telegram"):
        return RouterObservation("telegram.restart", "Telegram", True, True, True)
    if value.startswith("abre la calculadora"):
        return RouterObservation("windows.open", "calculadora", True, True)
    if value.startswith("cierra la calculadora"):
        return RouterObservation("windows.close", "calculadora", True, True)
    if value.startswith(("cancela la operacion",)):
        return RouterObservation("cancel", "operación", True, True)
    if value.startswith(("acuerdame", "recuerdame")):
        entity = "comprar pan" if "comprar pan" in value else "Atlas"
        return RouterObservation("reminder.create", entity, True, True)
    if "recordatorios tengo" in value:
        return RouterObservation("reminder.list")
    if value.startswith("cancela el recordatorio"):
        return RouterObservation("reminder.cancel", "Atlas", True, True)
    people = (("persona conocida uno", "persona_conocida_1"), ("persona conocida dos", "persona_conocida_2"))
    for phrase, entity in people:
        if phrase in value:
            intent = "people.greet" if value.startswith("saluda") else "people.introduce" if value.startswith("presenta") else "people.farewell" if value.startswith("despidete") else "people.presence"
            return RouterObservation(intent, entity)
    if "estado de atlas" in value:
        return RouterObservation("system.status", "Atlas")
    if value.startswith(("si, es correcto", "confirma la accion")):
        return RouterObservation("confirmation.accept")
    if value.startswith(("no, no era eso", "cancela y dejalo")):
        return RouterObservation("confirmation.reject")
    if value.startswith("repite tu respuesta"):
        return RouterObservation("repeat.response")
    if value.startswith("repite lo que he dicho"):
        return RouterObservation("repeat.user")
    if value.startswith("que has entendido"):
        return RouterObservation("repeat.transcript")
    if value.startswith("explicamelo"):
        return RouterObservation("continuity.followup")
    if value.startswith("dime algo divertido"):
        return RouterObservation("humor")
    if "tiempo hace" in value:
        return RouterObservation("weather")
    return RouterObservation("conversation")


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8-sig", newline="", closefd=True) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Graba y evalúa 160 casos sin ejecutar ninguna acción real.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--device")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    output = args.output or args.input.with_name("STT_CONVERSATION_BATTERY_160_RESULTS.csv")
    audio_dir = args.audio_dir or args.input.parent / "stt_human_audio"
    if not args.input.is_file():
        parser.error("No existe el CSV original.")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.input, output)
    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows, fields = list(reader), list(reader.fieldnames or [])
    if "confirmation_required_observed" not in fields:
        fields.append("confirmation_required_observed")
        for row in rows:
            row["confirmation_required_observed"] = ""

    recorder = ManualMicrophoneRecorder(device_name=args.device)
    if args.list_devices:
        print("\n".join(recorder.list_devices()))
        return 0
    selected = choose_microphone(recorder)
    config = STTConfig.from_env()
    stt = STTService(FasterWhisperSTTProvider(config), AudioConverter(timeout_seconds=min(30, config.timeout_seconds)), config=config, work_dir=audio_dir / ".converted")
    pending = [index for index, row in enumerate(rows) if not str(row.get("raw_transcript", "")).strip()]
    print(f"Micrófono: {selected}. Cobertura actual: {len(rows) - len(pending)}/{len(rows)}.")
    print("Modo router-only/dry-run: jamás se ejecutan comandos, Home Assistant ni acciones sensibles.")
    try:
        cursor = 0
        while cursor < len(pending):
            index = pending[cursor]
            row = rows[index]
            print(f"\nCaso {index + 1}/{len(rows)}\nDi exactamente:\n\"{row['expected_text']}\"")
            action = input("Enter=grabar, S=saltar temporalmente, Q=salir: ").strip().casefold()
            if action == "q":
                break
            if action == "s":
                cursor += 1
                continue
            target = audio_dir / f"stt_{int(row['id']):03d}.wav"
            recorder.start(target)
            try:
                input("Grabando. Pulsa Enter para detener…")
            finally:
                recorder.stop()
            result, _timings = stt.transcribe(target, language_hint="es", context_hint=row.get("category", "general"))
            normalized = ContextualTranscriptNormalizer.normalize(result)
            observed = inspect_router_only(normalized.text)
            print(f"Raw: {result.text}\nNormalizado: {normalized.text}\nIntent: {observed.intent}; entidad: {observed.entity or '-'}")
            decision = input("Enter=guardar, R=repetir, Q=guardar y salir: ").strip().casefold()
            if decision == "r":
                target.unlink(missing_ok=True)
                continue
            row.update({
                "audio_file": str(target.relative_to(output.parent)), "raw_transcript": result.text,
                "normalized_transcript": normalized.text, "observed_intent": observed.intent,
                "observed_entity": observed.entity, "command_observed": str(observed.command),
                "safe_action_observed": str(observed.safe_action),
                "confirmation_required_observed": str(observed.confirmation_required),
            })
            _write_csv(output, rows, fields)
            write_reports(rows, output.parent)
            cursor += 1
            if decision == "q":
                break
    finally:
        recorder.close()
    measured = sum(bool(str(row.get("raw_transcript", "")).strip()) for row in rows)
    print(f"Guardado: {output}\nCobertura: {measured}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
