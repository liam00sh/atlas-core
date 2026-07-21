# Línea base de Drive — ampliación del Sprint 17

Fecha: 19 de julio de 2026  
Entorno: cliente OAuth real de Atlas, raíz autorizada `Atlas Project`, alcance
`drive.readonly`, índice local temporal y Ollama local con
`nomic-embed-text`.

## Método

La medición se ejecutó con
`scripts/benchmark_drive_scoped_sprint17.py`. El índice activo de Atlas no se
modificó: todos los índices de la prueba se guardaron en un directorio
temporal. El informe no conserva contenido documental, tokens, credenciales ni
IDs de archivos individuales.

Para medir ramas con el contrato anterior se utilizó un adaptador que presenta
la carpeta objetivo como raíz virtual al algoritmo global existente. Por tanto,
los números representan el coste real de Drive y del indexador anterior, no el
nuevo código por ámbito.

## Resultados anteriores a la ampliación

| Escenario | Tiempo | Listados remotos | Descargas | Documentos | Fragmentos | Observaciones |
|---|---:|---:|---:|---:|---:|---|
| Raíz completa, primera pasada | 287,756 s | 60 | 336 | 328 | 2.596 | 8 archivos sin texto indexable |
| Raíz completa, sin cambios | 21,983 s | 60 | 8 | 328 | 2.596 | Los 8 no indexados se descargan otra vez |
| `00 - Documentación` | 19,032 s | 1 | 21 | 21 | 500 | Rama pequeña y documentalmente densa |
| `04 - Python` | 220,371 s | 43 | 303 | 295 | 2.063 | 8 archivos omitidos |
| Un archivo, descarga y fragmentación | 0,496 s | 0 | 1 | 1 | 2 | Archivo real seleccionado sin revelar su nombre |
| Embeddings de `00 - Documentación` | 85,273 s | 0 | 0 | 21 | 500 | 500 embeddings nuevos, dimensión 768 |
| Embeddings, segunda pasada sin cambios | 0,339 s | 0 | 0 | 21 | 500 | 500 reutilizados, 0 generados |

## Cuellos de botella observados

- La primera actualización global tarda 287,756 segundos y realiza 336
  descargas aunque una consulta posterior pueda necesitar solo una rama.
- Una segunda actualización global sin cambios todavía recorre 60 carpetas y
  tarda 21,983 segundos.
- Los ocho archivos que no producen fragmentos no quedan representados como
  omisiones persistentes; por ello vuelven a descargarse en la segunda pasada.
- La rama `00 - Documentación` tarda 19,032 segundos frente a 287,756 segundos
  de la raíz completa: un ámbito explícito evita trabajo remoto no relacionado.
- La reutilización semántica ya es eficaz cuando el índice documental no
  cambia: 85,273 segundos iniciales frente a 0,339 segundos sin cambios.

## Escenarios que no se indujeron en Drive real

No se modificaron, renombraron ni movieron archivos reales. La integración de
Atlas debe conservar el alcance de solo lectura y no sería correcto debilitarlo
para fabricar un benchmark. Esos casos se verificarán con dobles deterministas
en la suite automática. Si Drive ya contiene un cambio real durante una futura
medición, podrá observarse sin provocarlo.

## Datos reproducibles

Los contadores completos de esta ejecución están en
`data/performance/drive_baseline_sprint17.json`, una ruta de datos ignorada por
Git. El benchmark puede repetirse de forma explícita; nunca inicia OAuth
interactivo ni escribe en Drive.
