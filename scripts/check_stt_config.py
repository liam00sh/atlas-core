"""Diagnóstico y prueba STT local; nunca ejecuta Atlas ni autoriza descargas."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram_interface.media import TelegramMediaError, TelegramMediaValidator
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTError, STTResult, STTService
from voice.stt_diagnostics import collect_stt_diagnostics, nvidia_summary
from voice.stt_policy import STTDecision, STTDecisionKind, STTInputPolicy


@dataclass(frozen=True, slots=True)
class LiveSTTReport:
    result: STTResult
    decision: STTDecision
    timings_ms: dict[str, float]
    provider_health: dict[str, object]
    detected_mime: str


def _safe_config() -> STTConfig:
    # Esta herramienta jamás convierte una variable heredada en permiso de red.
    return replace(STTConfig.from_env(), allow_model_download=False)


def transcribe_local_audio(
    audio_path: str | Path,
    *,
    config: STTConfig | None = None,
    provider=None,
    converter=None,
    policy: STTInputPolicy | None = None,
    work_dir: str | Path | None = None,
) -> LiveSTTReport:
    target = Path(audio_path).expanduser()
    if not target.is_file():
        raise STTError("audio_not_found", "La ruta de audio no existe o no es un archivo.")
    safe_config = replace(config or STTConfig.from_env(), allow_model_download=False)
    try:
        detected_mime, _, _ = TelegramMediaValidator().validate(
            target,
            media_type="audio",
            max_bytes=25 * 1024 * 1024,
        )
    except (OSError, TelegramMediaError) as exc:
        raise STTError("audio_invalid_format", "La firma real no corresponde a un audio permitido.") from exc

    selected_provider = provider or FasterWhisperSTTProvider(safe_config)
    selected_converter = converter or AudioConverter(
        timeout_seconds=min(30.0, safe_config.timeout_seconds)
    )
    selected_policy = policy or STTInputPolicy()

    def run(directory: Path) -> LiveSTTReport:
        service = STTService(
            selected_provider,
            selected_converter,
            config=safe_config,
            work_dir=directory,
        )
        result, timings = service.transcribe(
            target,
            language_hint=safe_config.language_hint,
        )
        decision = selected_policy.evaluate(result)
        return LiveSTTReport(
            result=result,
            decision=decision,
            timings_ms=timings,
            provider_health=dict(selected_provider.health()),
            detected_mime=detected_mime,
        )

    if work_dir is not None:
        return run(Path(work_dir))
    with TemporaryDirectory(prefix="atlas-stt-live-") as temporary:
        return run(Path(temporary))


def _decision_label(kind: STTDecisionKind) -> str:
    return {
        STTDecisionKind.PROCESS: "PROCESS",
        STTDecisionKind.CONFIRM: "WAIT_FOR_CONFIRMATION",
        STTDecisionKind.REPEAT: "ASK_TO_REPEAT",
        STTDecisionKind.CLARIFY: "ASK_FOR_CLARIFICATION",
    }[kind]


def _metric(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _print_diagnostics(config: STTConfig, *, load_model: bool) -> int:
    print("Diagnóstico STT de Atlas (sin contenido de audio ni secretos)")
    if gpu := nvidia_summary():
        print(f"[OK] NVIDIA: {gpu}")
    checks = collect_stt_diagnostics(config=config, load_model=load_model)
    for item in checks:
        print(f"[{item.status}] {item.name}: {item.detail}")
    return 2 if any(item.status == "ERROR" for item in checks) else 0


def _print_live(report: LiveSTTReport, config: STTConfig) -> None:
    result = report.result
    health = report.provider_health
    print("\nPrueba STT local completa")
    print(f"Proveedor: {health.get('provider', 'desconocido')}")
    print(f"Dispositivo: {health.get('device', 'desconocido')}")
    print(f"Compute type: {health.get('compute_type', 'desconocido')}")
    print(f"Modelo: {config.model} (local)")
    print(f"Formato detectado: {report.detected_mime}")
    print(f"Idioma detectado: {result.language or 'desconocido'}")
    print(f"Duración: {_metric(result.duration_seconds)} s")
    print(f"Transcripción: {result.text}")
    print("Métricas Whisper/audio:")
    for name, value in (
        ("avg_logprob", result.avg_logprob),
        ("no_speech_probability", result.no_speech_probability),
        ("language_probability", result.language_probability),
        ("mean_word_probability", result.mean_word_probability),
        ("min_word_probability", result.min_word_probability),
        ("compression_ratio", result.compression_ratio),
        ("vad_speech_seconds", result.vad_speech_seconds),
        ("audio_rms", result.audio_rms),
        ("audio_peak", result.audio_peak),
        ("silence_ratio", result.silence_ratio),
        ("clipping_ratio", result.clipping_ratio),
        ("speech_score", result.confidence_score),
        ("audio.convert_ms", report.timings_ms.get("audio.convert")),
        ("stt.transcribe_ms", report.timings_ms.get("stt.transcribe")),
    ):
        print(f"  {name}: {_metric(value)}")
    print(f"Speech confidence: {result.confidence.value.upper()}")
    print(f"Intent: {report.decision.intent}")
    print(f"Intent confidence: {report.decision.intent_confidence.value.upper()}")
    print(f"Sensitive: {'YES' if report.decision.sensitive else 'NO'}")
    print(f"Decision: {_decision_label(report.decision.kind)}")
    if report.decision.response:
        print(f"Respuesta segura: {report.decision.response}")
    print("Atlas.process: NO LLAMADO")
    print("Persistencia/memoria: NO ESCRITA")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico y transcripción local privada de STT.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--load-model", action="store_true", help="Carga solo un modelo local; nunca descarga.")
    mode.add_argument("--live", metavar="RUTA_AUDIO", help="Valida, convierte y transcribe un audio local sin llamar a Atlas.")
    args = parser.parse_args(argv)
    config = _safe_config()
    if args.live:
        try:
            report = transcribe_local_audio(args.live, config=config)
        except STTError as exc:
            print(f"[ERROR] {exc.code}: {exc}")
            return 2
        _print_live(report, config)
        return 0
    return _print_diagnostics(config, load_model=bool(args.load_model))


if __name__ == "__main__":
    raise SystemExit(main())
