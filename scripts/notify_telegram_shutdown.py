"""Envía avisos de apagado, reinicio, suspensión y reanudación por Telegram."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram_interface.config import TelegramConfig, TelegramConfigError
from telegram_interface.env_loader import EnvFileError, load_env_file
from telegram_interface.storage import TelegramStorage

MESSAGES = {
    "shutdown": "Atlas se está apagando. Nos vemos cuando vuelva el equipo 👋",
    "critical_shutdown": "Windows ha iniciado un apagado crítico. Atlas se desconecta ahora.",
    "logoff": "La sesión de Windows se está cerrando. Atlas dejará de estar disponible.",
    "suspend": "El PC va a entrar en suspensión. Atlas quedará temporalmente desconectado 🌙",
    "resume": "El PC ha salido de suspensión. Atlas vuelve a estar disponible ⚡",
}


def _linked_chat_ids(storage: TelegramStorage) -> list[str]:
    chat_ids: list[str] = []
    for account in storage.section("accounts").values():
        if (
            isinstance(account, dict)
            and account.get("state") == "linked"
            and account.get("chat_id")
        ):
            chat_ids.append(str(account["chat_id"]))
    return chat_ids


def _send_direct(token: str, chat_id: str, text: str, timeout: float) -> tuple[bool, str]:
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Proyecto-Atlas-Windows-Lifecycle/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {details[:300]}"
    except urllib.error.URLError as exc:
        return False, f"red: {exc.reason}"
    except TimeoutError:
        return False, "timeout"
    except OSError as exc:
        return False, f"sistema: {exc}"

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return False, f"respuesta no JSON: {body[:300]}"

    if not result.get("ok"):
        return False, f"Telegram rechazó el envío: {body[:300]}"

    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="shutdown", choices=sorted(MESSAGES))
    parser.add_argument("--timeout", type=float, default=3.5)
    args = parser.parse_args()

    try:
        load_env_file(PROJECT_ROOT / ".env")
        config = TelegramConfig.from_env()
    except (EnvFileError, TelegramConfigError) as exc:
        print(f"No se pudo cargar Telegram: {exc}")
        return 2

    if not config.enabled or not config.token:
        print("Telegram está desactivado o no tiene token.")
        return 3

    storage = TelegramStorage(config.data_dir / "state.json")
    chat_ids = _linked_chat_ids(storage)
    if not chat_ids:
        print("No hay cuentas vinculadas con chat_id.")
        return 4

    sent = 0
    failed = 0
    for chat_id in chat_ids:
        ok, detail = _send_direct(
            token=config.token,
            chat_id=chat_id,
            text=MESSAGES[args.event],
            timeout=max(1.0, args.timeout),
        )
        if ok:
            sent += 1
            print(f"Enviado a {chat_id}.")
        else:
            failed += 1
            print(f"Fallo para {chat_id}: {detail}")

    print(
        f"Aviso {args.event}: enviados={sent}, fallos={failed}, "
        f"destinatarios={len(chat_ids)}."
    )
    return 0 if sent > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
