# Línea base de rendimiento — Sprint 17

Fecha: 19 de julio de 2026. Entorno: Windows, Python 3.14.6. Medición reproducible con `scripts/benchmark_sprint17.py`, `perf_counter`, `process_time`, `tracemalloc`, `cProfile` y contadores de I/O.

## Resultado anterior a optimizar

| Métrica | Línea base |
|---|---:|
| Construcción de `Atlas(ai_provider=None)` | 37.216 s |
| CPU durante construcción | 25.391 s |
| RAM actual tras arranque | 19.20 MB |
| Pico de RAM | 19.41 MB |
| Lecturas JSON del escenario | 1469 |
| Escrituras JSON | 1 |
| Saludo simple, primera/segunda | 60.487 / 52.209 ms |
| Memoria léxica, primera/segunda | 77.615 / 72.056 ms |
| KnowledgeRetriever, primera/segunda | 72.730 / 54.671 ms |
| Índice documental, primera/segunda | 0.399 / 0.341 ms |
| Herramienta, primera/segunda | 171.340 / 7.958 ms |
| Llamadas reales a Ollama | 0 |
| Llamadas remotas a Drive | 0 |

La medición externa usa proveedor desactivado y Drive local/no disponible para que sea repetible y no dependa de red. El escenario extendido posterior verifica por separado una ruta local simulada: una comprobación, una generación y medición del prompt.

## Cuello de botella demostrado

`FamilyInitializer.initialize()` consumía 34.061 s de los 37.216 s. Durante el arranque se observaron:

- 509 llamadas a `load_relationships()`;
- 911 cargas de personas;
- 129.286 deserializaciones `Relationship.from_dict()`;
- 1469 lecturas JSON totales.

El coste procedía de releer y deserializar los mismos tres archivos durante comprobaciones idempotentes. No procedía de Ollama, Drive, RAG ni construcción de prompts.

Evidencia cruda: `performance_baseline_sprint17.json`.

