"""Aplica de forma controlada la integración de modos de respuesta."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def replace_once(
    path: Path,
    old: str,
    new: str,
) -> None:
    content = path.read_text(encoding="utf-8")
    if new in content:
        print(f"Ya aplicado: {path.relative_to(ROOT)}")
        return
    if old not in content:
        raise RuntimeError(
            f"No se encontró el bloque esperado en {path}."
        )
    path.write_text(
        content.replace(old, new, 1),
        encoding="utf-8",
    )
    print(f"Actualizado: {path.relative_to(ROOT)}")


def main() -> int:
    storage = ROOT / "telegram_interface" / "storage.py"
    gateway = ROOT / "telegram_interface" / "gateway.py"

    replace_once(
        storage,
        'return {"version": 3, "accounts": {}, "link_codes": {}, "sessions": {}, "deliveries": {}, "reply_context": {}, "lifecycle": {}, "offset": 0}',
        'return {"version": 4, "accounts": {}, "link_codes": {}, "sessions": {}, "deliveries": {}, "reply_context": {}, "lifecycle": {}, "response_modes": {}, "offset": 0}',
    )

    replace_once(
        gateway,
        'from telegram_interface.rate_limiter import TelegramRateLimiter\n',
        'from telegram_interface.rate_limiter import TelegramRateLimiter\n'
        'from telegram_interface.response_modes import (\n'
        '    TelegramResponseModeStore,\n'
        '    confirmation_text,\n'
        '    detect_response_mode_directive,\n'
        ')\n',
    )

    replace_once(
        gateway,
        '        self.clock = clock\n',
        '        self.clock = clock\n'
        '        storage = getattr(linker, "storage", None)\n'
        '        self.response_modes = (\n'
        '            TelegramResponseModeStore(storage)\n'
        '            if storage is not None\n'
        '            else None\n'
        '        )\n',
    )

    marker = (
        '            command, argument = self._command(message.text)\n'
        '            if command:\n'
    )
    replacement = (
        '            command, argument = self._command(message.text)\n'
        '            mode_directive = (\n'
        '                detect_response_mode_directive(message.text)\n'
        '                if atlas_user_id else None\n'
        '            )\n'
        '            if (\n'
        '                mode_directive is not None\n'
        '                and self.response_modes is not None\n'
        '                and atlas_user_id is not None\n'
        '            ):\n'
        '                self.response_modes.set(\n'
        '                    atlas_user_id,\n'
        '                    mode_directive,\n'
        '                )\n'
        '                response = GatewayResponse(\n'
        '                    confirmation_text(mode_directive)\n'
        '                )\n'
        '            elif command:\n'
    )
    replace_once(gateway, marker, replacement)

    print("Integración aplicada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
