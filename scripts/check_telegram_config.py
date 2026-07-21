"""Comprobacion segura de Telegram sin imprimir secretos."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram_interface.client import TelegramBotClient, TelegramClientError
from telegram_interface.config import TelegramConfig, TelegramConfigError
from telegram_interface.env_loader import EnvFileError, load_env_file
from telegram_interface.storage import TelegramStorage


def main() -> int:
    try:
        load_env_file(PROJECT_ROOT / ".env")
    except EnvFileError as exc:
        print(f"Configuracion local no valida: {exc}")
        return 2
    parser = argparse.ArgumentParser(description="Valida la configuracion Telegram de Atlas.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", action="store_true", help="No realiza conexiones de red.")
    mode.add_argument("--live", action="store_true", help="Comprueba getMe y webhook manualmente.")
    args = parser.parse_args()
    try:
        config = TelegramConfig.from_env()
    except TelegramConfigError as exc:
        print(f"Configuracion no valida: {exc}")
        return 2
    print(f"Telegram activado: {config.enabled}")
    print(f"Token presente: {config.token_present}")
    try:
        TelegramStorage(config.data_dir / "state.json").snapshot()
    except OSError:
        print("Almacenamiento accesible: no")
        return 3
    print("Almacenamiento accesible: si")
    try:
        from core.atlas import Atlas  # noqa: F401
    except ImportError:
        print("Integracion con Atlas disponible: no")
        return 4
    print("Integracion con Atlas disponible: si")
    if args.offline:
        print("Conexion real: omitida (--offline)")
        return 0
    if not config.enabled or not config.token:
        print("Conexion real: Telegram esta desactivado o falta el token.")
        return 5
    try:
        client = TelegramBotClient(config.token)
        bot = client.get_me()
        webhook = client.get_webhook_info()
    except TelegramClientError as exc:
        print(f"Conexion real: error seguro ({exc.code})")
        return 6
    print(f"Identidad del bot valida: {bool(bot.get('id'))}")
    print(f"Webhook ausente: {not bool(str(webhook.get('url', '')).strip())}")
    print("Long polling permitido: si" if not webhook.get("url") else "Long polling permitido: no")
    return 0 if not webhook.get("url") else 7


if __name__ == "__main__":
    raise SystemExit(main())
