# Integración inicial de voces alternativas

## Alcance

Esta entrega añade la base modular del subsistema de voz:

- catálogo de voces;
- preferencias de voz por usuario;
- resolución de fallback;
- contrato TTS;
- adaptador desacoplado para Kokoro;
- pruebas unitarias.

No activa todavía la voz en `main.py`, no modifica Telegram y no incluye STT,
wake word ni las voces oficiales.

## Voces registradas

| Identificador | Motor | Voz | Región |
|---|---|---|---|
| `daxter_official` | pendiente | oficial | España |
| `daxter_alex` | Kokoro | `em_alex` | Latinoamérica |
| `daxter_santa` | Kokoro | `em_santa` | Latinoamérica |
| `coco_official` | pendiente | oficial | España |
| `coco_dora` | Kokoro | `ef_dora` | Latinoamérica |

La voz oficial permanece como opción predeterminada. Un usuario puede elegir
una alternativa permanentemente. Ese uso voluntario no se considera fallo.

## Separación de entornos

Atlas Core permanece en Python 3.14. Kokoro se ejecuta mediante
`tools/kokoro_bridge.py` dentro de su entorno Python 3.12.

Configura el comando mediante:

```powershell
$env:ATLAS_KOKORO_COMMAND = '"C:\ruta\.venv\Scripts\python.exe" "C:\ruta\atlas_core\tools\kokoro_bridge.py"'
```

Para persistirlo en Windows:

```powershell
setx ATLAS_KOKORO_COMMAND '"C:\ruta\.venv\Scripts\python.exe" "C:\ruta\atlas_core\tools\kokoro_bridge.py"'
```

## Pruebas

```powershell
python -m pytest -q tests/test_voice_catalog.py tests/test_voice_preferences.py tests/test_voice_resolver.py
```

La integración con el perfil persistente real de cada usuario se realizará
después de validar dónde guarda actualmente Atlas los campos adicionales del
perfil.
