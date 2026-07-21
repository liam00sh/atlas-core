"""Punto de entrada manual del servicio long polling de Atlas."""

from __future__ import annotations

from pathlib import Path
import signal
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.models.model_registry import ModelRegistry
from ai.providers.ollama_provider import OllamaProvider
from core.atlas import Atlas
from telegram_interface.config import TelegramConfig, TelegramConfigError
from telegram_interface.env_loader import EnvFileError, load_env_file
from telegram_interface.instance_lock import TelegramInstanceLock, TelegramInstanceLockedError
from telegram_interface.runtime import build_runtime


def main() -> int:
    try:
        load_env_file(PROJECT_ROOT / ".env")
    except EnvFileError as exc:
        print(f"Configuracion local no valida: {exc}")
        return 2
    try:
        config = TelegramConfig.from_env()
    except TelegramConfigError as exc:
        print(f"Telegram no puede arrancar: {exc}")
        return 2
    if not config.enabled:
        print("Telegram esta desactivado. La CLI de Atlas no se ve afectada.")
        return 0
    lock = TelegramInstanceLock(config.data_dir / "polling.lock")
    try:
        lock.acquire()
    except TelegramInstanceLockedError as exc:
        print(str(exc))
        return 3
    runtime = None
    try:
        # Telegram debe utilizar exactamente el mismo proveedor de IA local
        # que la CLI. Antes se construía Atlas() sin proveedor, por lo que el
        # bot nunca podía alcanzar Ollama aunque la consola sí pudiera.
        model_registry = ModelRegistry()
        ai_provider = OllamaProvider(
            model_name=model_registry.get_default_model_name(),
            timeout=180,
        )
        atlas = Atlas(ai_provider=ai_provider)
        runtime = build_runtime(atlas, config)
        signal.signal(signal.SIGINT, lambda *_: runtime.poller.stop())
        signal.signal(signal.SIGTERM, lambda *_: runtime.poller.stop())
        print("Atlas Telegram iniciado mediante long polling. Token presente: si.")
        runtime.poller.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Telegram se detuvo de forma segura: {type(exc).__name__}.")
        return 4
    finally:
        if runtime is not None:
            runtime.close()
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
