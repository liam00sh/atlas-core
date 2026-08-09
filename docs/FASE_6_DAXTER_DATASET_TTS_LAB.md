# Fase 6 — cierre del dataset Daxter y laboratorio TTS

Estado: dataset listo para evaluación y Ronda A completada. No se ha elegido una voz ganadora ni se han iniciado adaptaciones o entrenamientos largos.

## Evidencia del dataset

La auditoría se ejecutó contra el maestro de 1.300 filas y los WAV originales de `02_limpios`. El CSV maestro no se modificó y su SHA-256 es:

```text
cc461a9e38e4ec13d9a80b726d5b9c6572a6b4a47eff293ea018d23d6cbc5f13
```

Resultados:

- 1.300 muestras y 1.300 identificadores únicos;
- 1.300 WAV legibles y 1.300 hashes coincidentes;
- 49 min 12,479 s de audio;
- 0 errores, 2 avisos y 7 muestras marcadas para revisión;
- 0 grupos de duplicados exactos y 0 candidatos acústicos duplicados;
- 1.300 muestras marcadas como utilizables para TTS.

La herramienta `tools/audit_daxter_dataset.py` genera el informe completo, las excepciones, estadísticas, manifiesto y sumas SHA-256. Rechaza un cierre si cambia el número esperado de filas, el hash del maestro, falta un WAV, un archivo no es PCM legible o no coincide su hash.

Ejemplo reproducible:

```powershell
python tools/audit_daxter_dataset.py `
  --metadata <metadata_daxter_final.csv> `
  --audio-root <02_limpios> `
  --output-dir <auditoria_1060> `
  --expected-rows 1300 `
  --expected-metadata-sha256 cc461a9e38e4ec13d9a80b726d5b9c6572a6b4a47eff293ea018d23d6cbc5f13
```

Los clips más largos y los dos extremos con silencio quedan visibles en `AUDIO_AUDIT_EXCEPTIONS.csv`; no se han descartado automáticamente ni se ha cambiado su transcripción.

## Referencias de voz

El manifiesto selecciona nueve referencias de Jak II con distintas emociones y calidad disponible `buena`. La referencia combinada de laboratorio concatena tres de ellas —neutral, emocionada y asustada— en un WAV mono de 48 kHz y 12,36 s. Esta selección es evidencia para las pruebas, no una modificación del dataset.

## Ronda A local

La batería común contiene trece frases en español: neutra, sonriente, traviesa, sorprendida, emocionada, asustada, enfadada, curiosa, confiada, determinada, juguetona, números y nombres, y una frase larga. Los motores se ejecutaron en Windows 11 con una RTX 4060:

| Motor | Modalidad | Salidas | Frecuencia | RTF medio | VRAM pico | Similitud ECAPA media |
|---|---|---:|---:|---:|---:|---:|
| Chatterbox Multilingual 0.1.7 | clonación zero-shot | 13/13 | 24 kHz | 1,225 | 4.529,9 MB | 0,69232 |
| Chatterbox + OpenVoice V2 | TTS y conversión de voz | 13/13 | 22,05 kHz | 0,165 | 717,8 MB | 0,65335 |

Todas las salidas son WAV mono PCM de 16 bits. La métrica ECAPA es orientativa y no sustituye la escucha. Chatterbox produjo duraciones anómalas en los casos `09_confiado` y `12_numeros_nombres`; deben escucharse para detectar pausas, repetición o alucinación. OpenVoice usa esas mismas tomas como fuente y puede heredar el problema.

El reproductor ciego y `HUMAN_LISTENING_TEST.csv` mantienen vacías las puntuaciones humanas. La decisión de voz se tomará tras esa escucha. Sólo un candidato prometedor podrá pasar después a una adaptación ligera; la Ronda C de entrenamiento largo permanece fuera de alcance.

## Límites y seguridad

- El dataset, las referencias, los modelos y los WAV generados permanecen locales y están excluidos por `.gitignore`.
- Los scripts no integran aún ningún motor en Atlas y no cambian su fallback de voz.
- No se aceptaron en nombre del usuario licencias o términos adicionales; por ello XTTS-v2 no se ejecutó.
- No se declara ganador ni cierre global de la Fase 6.
- El intento inicial contra `04_normalizados` se conserva separado como evidencia de raíz inválida; sus hashes no correspondían al maestro de 48 kHz.

## Verificación del código

Las pruebas cubren la aceptación del dataset válido, el rechazo de hash incorrecto, la batería común y las utilidades WAV. La validación de entrega incluye pruebas focalizadas, colección completa, suite completa, compilación y comprobación final del estado de Git y del hash del maestro.
