# Preferencias persistentes y prosodia natural

## Alcance

Esta entrega añade:

- persistencia de preferencias de voz por usuario;
- selección de voz por identidad;
- activación o desactivación del fallback;
- conservación de párrafos;
- segmentación segura por puntuación;
- pausas controladas entre fragmentos;
- pruebas unitarias de persistencia y prosodia.

## Pausas iniciales

- coma: 150 ms;
- punto y coma y dos puntos: 280 ms;
- punto, interrogación y exclamación: 420 ms;
- puntos suspensivos: 600 ms;
- punto y aparte: 760 ms.

La segmentación evita cortar decimales, direcciones IP y abreviaturas comunes.

## Preferencias por usuario

Se guardan en:

```text
data/voice/user_preferences.json
```

Ejemplo:

```json
{
  "Alex": {
    "daxter_voice_id": "daxter_alex",
    "coco_voice_id": "coco_dora",
    "fallback_enabled": true,
    "notify_voice_fallback": true,
    "speech_rate": 1.0,
    "speech_volume": 1.0
  }
}
```

## Configuración local temporal mediante CLI

```powershell
python -m tools.voice_preferences_cli --user Alex --show
python -m tools.voice_preferences_cli --user Alex --identity daxter --voice daxter_alex
python -m tools.voice_preferences_cli --user Alex --identity daxter --voice daxter_santa
python -m tools.voice_preferences_cli --user Alex --identity coco --voice coco_dora
python -m tools.voice_preferences_cli --user Alex --fallback on
```

La integración de estos cambios como comandos conversacionales internos de Atlas
queda para la siguiente iteración, una vez validada la persistencia y la
prosodia de extremo a extremo.
