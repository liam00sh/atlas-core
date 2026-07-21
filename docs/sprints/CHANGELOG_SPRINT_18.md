# Changelog — Sprint 18

## Archivos creados

- `.env.example`
- `telegram_interface/__init__.py`
- `telegram_interface/audit.py`
- `telegram_interface/client.py`
- `telegram_interface/config.py`
- `telegram_interface/core_adapter.py`
- `telegram_interface/formatter.py`
- `telegram_interface/gateway.py`
- `telegram_interface/identity_linker.py`
- `telegram_interface/instance_lock.py`
- `telegram_interface/models.py`
- `telegram_interface/polling.py`
- `telegram_interface/rate_limiter.py`
- `telegram_interface/runtime.py`
- `telegram_interface/session_manager.py`
- `telegram_interface/storage.py`
- `tools/telegram_accounts.py`
- `scripts/check_telegram_config.py`
- `scripts/run_telegram_bot.py`
- `tests/telegram/__init__.py`
- `tests/telegram/conftest.py`
- `tests/telegram/test_client_storage_lock.py`
- `tests/telegram/test_config_security.py`
- `tests/telegram/test_core_tool_integration.py`
- `tests/telegram/test_formatter_rate_sessions.py`
- `tests/telegram/test_gateway_commands.py`
- `tests/telegram/test_identity_linking.py`
- `tests/telegram/test_polling.py`
- `docs/sprints/SPRINT_18_TELEGRAM_INTEGRATION.md`
- `docs/sprints/TEST_RESULTS_SPRINT_18.md`
- `docs/sprints/CHANGELOG_SPRINT_18.md`
- `INSTRUCCIONES_SPRINT_18.md`

## Archivos modificados

- `.gitignore`: permite `.env.example` y excluye datos Telegram.
- `core/atlas.py`: registra almacenamiento, vinculador y herramienta local.
- `core/atlas_users.py`: impide cambios de usuario que contradigan la identidad
  autenticada del canal Telegram.
- `tools/atlas_adapter.py`: permisos administrativos locales y contexto
  autoritativo con intersección de permisos por canal.

## Capacidades

- `telegram.link.confirm`
- `telegram.admin.revoke`

## Permisos

- `telegram.use`
- `telegram.unlink`
- `telegram.admin_link`
- `telegram.admin_revoke`

No se concede ningún permiso sensible adicional.

No se modificó `requirements.txt`: la integración usa exclusivamente la
biblioteca estándar de Python.

## Compatibilidad

- `main.py` no se modifica.
- La CLI no necesita token ni importa un servicio activo.
- Se conservan ambos frameworks de herramientas.
- Google Drive continúa en lectura.
- No se implementan webhook, Telegram multimedia, grupos ni integraciones de
  sprints posteriores.
