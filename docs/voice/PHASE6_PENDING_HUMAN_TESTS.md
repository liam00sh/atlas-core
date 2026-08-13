# Fase 6 · pruebas humanas pendientes

La Fase 6 permanece abierta. Este bloque no sustituye ni reescribe las evaluaciones humanas anteriores.

## Comparación de voz

El mini-lab B1 de 24 muestras ya fue escuchado. Conserva bien la identidad de Daxter, pero el español peninsular es insuficiente y se observaron pronunciaciones no peninsulares, problemas con *Home Assistant* y artefactos/cortes en varias muestras.

La nueva comparación privada enfrenta, con el mismo texto y referencia:

1. Chatterbox Multilingual V2 (B1).
2. Chatterbox Multilingual V3.
3. Chatterbox Multilingual: Spanish (Spain), ajuste específico del Single Language Pack.

No existe ganador hasta completar la escucha A/B/C. Las métricas automáticas no deciden.

## STT humana 160

La batería pública define 160/160 casos, pero antes de esta intervención tenía 0/160 grabaciones. `tools/run_stt_human_battery.py` crea una copia de resultados, selecciona micrófono, graba cada caso, transcribe, normaliza e inspecciona el contrato del router sin importar ni llamar ejecutores. Es reanudable y nunca ejecuta comandos, Home Assistant ni acciones sensibles.

El resultado final solo es válido cuando la cobertura es 160/160. Se conservan por separado texto raw y normalizado, WER de ambos, y exactitud de intención, entidad, comando y acción segura por categoría.

## Home Assistant

La discrepancia física/UI/API de la luz del acuario pequeño sigue sin causa demostrada. `tools/diagnose_home_assistant_entity.py` resuelve el alias, enumera entidades parecidas y toma lecturas tras `turn_on` y `turn_off` a 0, 0,25, 0,5, 1, 2, 3, 5 y 10 segundos. Las acciones requieren `--run-actions` y una confirmación explícita. El diagnóstico no modifica el router productivo.

## E2E

`tools/run_voice_e2e_guided.py` recorre trece turnos reales y registra de forma incremental STT, respuesta, TTS, confirmación/cancelación, contexto, recordatorio y observaciones físicas. La prueba debe realizarse separada de la escucha TTS y de la batería STT 160.

## Datos que no se publican

No se versionan WAV humanos o generados, checkpoints, resultados humanos, datasets, informes privados, nombres familiares ni archivos `.env`.
