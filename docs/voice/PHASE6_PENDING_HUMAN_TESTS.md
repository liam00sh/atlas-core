# Fase 6 · pruebas humanas pendientes

La Fase 6 permanece abierta. Este bloque no sustituye ni reescribe las evaluaciones humanas anteriores.

## Comparación de voz

El mini-lab B1 de 24 muestras ya fue escuchado. Conserva bien la identidad de Daxter, pero el español peninsular es insuficiente y se observaron pronunciaciones no peninsulares, problemas con *Home Assistant* y artefactos/cortes en varias muestras.

La nueva comparación privada enfrenta, con el mismo texto y referencia:

1. Chatterbox Multilingual V2 (B1).
2. Chatterbox Multilingual V3.
3. Chatterbox Multilingual: Spanish (Spain), ajuste específico del Single Language Pack.

La escucha ciega de 84 evaluaciones ya se completó. El paquete oficial `es-ES`
es el ganador humano: obtuvo 11 primeros puestos, la mejor media global
(4,030/5), la mejor valoración de español de España (4,250/5) y la menor
incidencia de artefactos/cortes (4,929/5). V2 queda segundo y conserva una
ligera ventaja de identidad (4,107 frente a 3,964). La configuración `es-ES`
queda congelada como candidata, no como cierre de Fase 6: persisten errores en
palabras con tilde, naturalidad/ritmo y cortes puntuales. Las métricas
automáticas se conservan como diagnóstico y no decidieron.

La fuente humana contiene una anomalía conservada sin corrección: las tres
variantes de `TTS023` recibieron el puesto 2.º. El procesador la declara en su
sección de integridad y nunca cambia puntuaciones, preferencias o comentarios.

## STT humana 160

La batería pública define 160/160 casos. El primer intento conservó su WAV,
pero falló porque la herramienta heredaba el modelo predeterminado `small` sin
ruta local, en vez de la configuración `medium` usada por el recorrido de voz
de PC. `tools/run_stt_human_battery.py` acepta ahora modelo, ruta, dispositivo
de cálculo y tipo de cómputo explícitos; bloquea descargas y ejecuta un preflight
que carga y prueba la transcripción antes de elegir o abrir el micrófono.

El CSV registra estados incrementales (`not_recorded`, `recorded`,
`pending_transcription`, `transcribed`, `evaluated`, `skipped` y `error`),
confianza, correcciones y errores. Si STT falla, el WAV se conserva y el mismo
audio se reintenta sin obligar a grabar otra vez. `--smoke-test` limita una
sesión a tres casos. La inspección sigue siendo router-only/dry-run y nunca
ejecuta comandos, Home Assistant ni acciones sensibles.

El resultado final solo es válido cuando la cobertura es 160/160. Se conservan por separado texto raw y normalizado, WER de ambos, y exactitud de intención, entidad, comando y acción segura por categoría.

## Home Assistant

La prueba física completada sobre la entidad exacta dio `on` y `off`
coherentes en dispositivo, interfaz y API: el fallo histórico físico ON/API
OFF queda como **NOT_REPRODUCED**, no como borrado ni demostrado resuelto. La
respuesta inmediata del servicio y las lecturas de 0 y 0,25 s conservaron el
estado anterior; la API confirmó el nuevo estado a 0,5 s y permaneció estable.
Esto demuestra una ventana stale capaz de explicar una lectura prematura, pero
no la causa exacta del incidente histórico. El adaptador ya espera y verifica;
una regresión reproduce expresamente la ventana stale de 250 ms.

## E2E

`tools/run_voice_e2e_guided.py` recorre trece turnos reales y registra de forma incremental STT, respuesta, TTS, confirmación/cancelación, contexto, recordatorio y observaciones físicas. La prueba debe realizarse separada de la escucha TTS y de la batería STT 160.

## Datos que no se publican

No se versionan WAV humanos o generados, checkpoints, resultados humanos, datasets, informes privados, nombres familiares ni archivos `.env`.
