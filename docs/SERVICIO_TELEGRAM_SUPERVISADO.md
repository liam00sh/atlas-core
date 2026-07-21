# Atlas Telegram — servicio supervisado en Windows

## Objetivo

- Arranque automático al iniciar sesión en Windows.
- Ejecución oculta e independiente de cualquier terminal.
- Reinicio automático si el bot termina.
- Recarga automática al modificar archivos Python o configuración relevante.
- Espera a que la unidad del proyecto esté disponible.

## Arquitectura

Programador de tareas → bootstrap local en `%LOCALAPPDATA%` → supervisor Python → bot Telegram.

El bootstrap local permite que la tarea arranque aunque la unidad `H:` todavía no se haya montado. El supervisor mantiene un único proceso del bot y observa cambios en el código.

## Recarga automática

El supervisor observa archivos fuente de:

- `core/`
- `telegram_interface/`
- `assistant_identity/`
- `conversation/`
- `memory/`
- `knowledge/`
- `tools/`
- `ai/`
- `scripts/*.py`
- `.env`
- `config.py`

Los cambios en `data/`, `logs/`, pruebas o cachés no reinician el bot.

Cuando detecta cambios espera brevemente para que termine la sincronización del archivo y reinicia solo el proceso Telegram. No reinicia Windows, Telegram móvil, las vinculaciones ni los datos persistentes.
