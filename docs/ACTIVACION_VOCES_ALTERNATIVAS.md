# Activación operativa de las voces alternativas

## Objetivo

Activar síntesis y reproducción de las respuestas visibles en la consola de
Atlas, manteniendo Kokoro en su entorno Python 3.12 independiente.

## Variables necesarias

Ejemplo adaptado al laboratorio actual:

```powershell
setx ATLAS_VOICE_ENABLED "true"
setx ATLAS_DAXTER_VOICE "daxter_official"
setx ATLAS_COCO_VOICE "coco_official"
setx ATLAS_VOICE_SPEAK_CONSOLE_OUTPUT "true"
setx ATLAS_KOKORO_COMMAND '"REDACTED_ad35dfb21264\Emuladores\02 - Voz alternativa\01 - Laboratorio\.venv\Scripts\python.exe" "C:\Proyectos\Atlas\atlas_core\tools\kokoro_bridge.py"'
```

Después de usar `setx`, se debe cerrar y volver a abrir PowerShell o reiniciar
el launcher de Atlas para que el proceso reciba las variables.

Mientras las voces oficiales estén deshabilitadas:

- Daxter oficial se resolverá como `daxter_alex`;
- Coco oficial se resolverá como `coco_dora`;
- `daxter_santa` puede configurarse manualmente.

## Prueba manual aislada

```powershell
python tools/test_voice_runtime.py --identity daxter --voice daxter_alex
python tools/test_voice_runtime.py --identity daxter --voice daxter_santa
python tools/test_voice_runtime.py --identity coco --voice coco_dora
```

## Prueba con Atlas

```powershell
python main.py
```

Las respuestas impresas por `Atlas.process()` se mantienen visibles y se
reproducen después mediante la voz correspondiente.

## Desactivación inmediata

```powershell
setx ATLAS_VOICE_ENABLED "false"
```

La voz es opcional. Si falla, Atlas mantiene la respuesta escrita.
