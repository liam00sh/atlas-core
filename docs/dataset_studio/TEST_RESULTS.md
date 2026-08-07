# Resultados de pruebas — Atlas Dataset Studio v1

Fecha: 7 de agosto de 2026.

## Automatización específica

La suite usa WAV PCM diminutos creados en carpetas temporales. No importa Atlas, no carga identidades, no contacta proveedores y no escribe en el dataset real.

Resultado inicial de la suite específica: `17 passed`. Cubre carga y migración v1, preservación de campos, búsqueda, filtros, navegación e historial, texto protegido, etiquetado múltiple, personalidad, conversación, autosave, escritura atómica, snapshots, recuperación, locks, lock huérfano, modo lectura, cambios externos, heurística no destructiva, esquemas CSV/JSONL corruptos, validación WAV/hash, archivos ausentes, duplicados, manifiesto, exportaciones e interfaz/atajos.

Durante la prueba se reprodujo un bloqueo transitorio de Windows entre autosaves consecutivos. Se añadió reintento acotado al reemplazo atómico y la prueba pasó después de la corrección.

## Suite completa de Atlas

Resultado: `1087 passed, 1 skipped, 2324 subtests passed` en 162,77 s. Los SHA-256 de `identity/data/people.json`, `animals.json` y `relationships.json` fueron idénticos antes y después.

## Prueba controlada con el dataset real

Se copió `metadata_daxter.csv` a una carpeta temporal; los WAV originales se mantuvieron en lectura. Resultados:

- 1.300 muestras abiertas en 0,0293 s;
- duración detectada: 2.952,4785 s (49m 12s);
- filtros de texto, juego y estado correctos;
- etiquetas, autosave, cierre y reapertura conservaron cambios en la copia;
- exportación completa y hashes en 0,9367 s;
- validación `VALID`, cero errores y advertencia correcta por muestras pendientes;
- siete archivos de salida generados sin rutas absolutas;
- tres WAV del inicio, mitad y final cargados y avanzaron en reproducción con Qt Multimedia;
- arranque real de `python -m atlas_dataset_studio --project ... --read-only --smoke-test` correcto.

Hashes del dataset original antes y después de la prueba:

- `metadata_daxter.csv`: `08fe1651b4f5e5696cc4526e2090fc67ffbe6672e23a400c4e505ab1eb953835`;
- `metadata_daxter.jsonl`: `0c7550bd0d7d503c8d173e02d7d3ccb1a0c31809ee730a926fffdaf757321059`;
- `revision_humana.csv`: `936aadc830e44e32a62189f4356058c3f7488f4ef2f64113093a8c2474bcde80`.

Los tres hashes permanecieron idénticos. El dataset real no fue escrito.

## Estado

La herramienta está técnicamente preparada para comenzar la revisión humana sobre el dataset de Daxter. El dataset, correctamente, no está cerrado: sus 1.300 filas reales siguen en `pending_review` hasta que se etiqueten.
