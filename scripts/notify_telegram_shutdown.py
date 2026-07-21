"""Envía el aviso de apagado de Telegram antes de detener los procesos."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram_interface.client import TelegramBotClient
from telegram_interface.config import TelegramConfig, TelegramConfigError
from telegram_interface.env_loader import EnvFileError, load_env_file
from telegram_interface.lifecycle import TelegramLifecycleNotifier
from telegram_interface.storage import TelegramStorage


def main() -> int:
    try:
        load_env_file(PROJECT_ROOT / ".env")
        config = TelegramConfig.from_env()
    except (EnvFileError, TelegramConfigError) as exc:
        print(f"No se pudo cargar Telegram: {exc}")
        return 2
    if not config.enabled or not config.token:
        return 0
    storage = TelegramStorage(config.data_dir / "state.json")
    notifier = TelegramLifecycleNotifier(storage, TelegramBotClient(config.token))
    sent = notifier.notify_stopping()
    print(f"Aviso de apagado enviado a {sent} cuenta(s) vinculada(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
