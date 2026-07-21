# Corrección Sprint 9 — Índice rápido y relaciones encadenadas

## Índice de Drive

El retraso no se debía a que Atlas estuviese recorriendo todo Mi unidad. La
restricción a `Atlas Project` estaba activa, pero el cliente verificaba los
ancestros de cada archivo individualmente. Además, el índice entraba en
carpetas técnicas como `.git`, cachés y `Releases`.

La corrección:

- mantiene el alcance exclusivamente en `Atlas Project`;
- valida cada carpeta una sola vez;
- reutiliza metadatos ya obtenidos;
- considera automáticamente seguros los hijos de una carpeta autorizada;
- excluye `.git`, `.agents`, cachés, entornos virtuales, logs y Releases;
- descarta ZIP, 7Z, RAR, EXE, DLL, ISO, BIN y otros binarios antes de intentar
  descargarlos;
- conserva la sincronización incremental;
- sube la versión del índice a 3 para reconstruirlo limpiamente.

## Relaciones encadenadas

El resolvedor anterior solo entendía una relación exterior con una persona
nombrada o con el usuario actual.

Ahora evalúa expresiones recursivas de hasta ocho pasos:

```text
mi novia
hermano de mi novia
madre de mi novia
tía de Saray
hija de la tía de Saray
```

Cada paso se valida contra `RelationshipEngine`; no se deducen nombres mediante
el modelo local.

## Archivos reemplazados

```text
tools/google_drive_oauth.py
tools/google_drive_index.py
core/atlas_ai.py
tests/test_conversation_identity_regressions.py
```

## Archivos nuevos

```text
tests/tools/test_google_drive_index_performance.py
```
