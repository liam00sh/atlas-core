# Resultados de pruebas — Sprint 17

Fecha: 19 de julio de 2026. Python 3.14.6.

```text
python -m pytest tests/memory -q
48 passed in 13.56s
0 failed
```

```text
python -m pytest tests/knowledge -q
17 passed in 1.19s
0 failed
```

```text
python -m pytest tests/tools -q
106 passed in 15.71s
0 failed
```

```text
python -m pytest tests -q
484 passed, 2324 subtests passed in 636.40s (0:10:36)
0 failed
```

Las cuatro pruebas nuevas verifican reutilización, copias independientes, invalidación por escritura, invalidación por cambio externo, límite y aislamiento entre instancias.

## Ampliación de Drive por ámbitos

Ejecución definitiva del 19 de julio de 2026:

```text
python -m pytest tests/memory -q
48 passed in 11.86s
0 failed
```

```text
python -m pytest tests/knowledge -q
18 passed in 1.44s
0 failed
```

```text
python -m pytest tests/tools -q
143 passed in 17.00s
0 failed
```

```text
python -m pytest tests -q
522 passed, 2324 subtests passed in 520.10s (0:08:40)
0 failed
```

Se añadieron 38 pruebas respecto a las 484 anteriores. Cubren resolución
absoluta y relativa, raíz, `..`, nombres duplicados, breadcrumbs, árbol,
usuario/sesión, TTL, permisos, sincronización global, carpeta recursiva y
directa, archivo, revisiones sin cambios, vacíos, renombrados, movimientos,
eliminaciones, listados truncados, errores temporales, preservación de otras
ramas, búsqueda léxica/semántica por ámbito, propagación a
`KnowledgeRetriever` y conversación natural.

Los benchmarks reales están separados de pytest. La suite general no necesita
credenciales, Drive, red ni Ollama.

## Validación transversal de todas las ramas de Atlas Project

Ejecución definitiva posterior al cierre transversal:

```text
python -m pytest tests/memory -q
48 passed in 12.72s
0 failed
```

```text
python -m pytest tests/knowledge -q
18 passed in 1.26s
0 failed
```

```text
python -m pytest tests/tools -q
165 passed in 19.63s
0 failed
```

```text
python -m pytest tests -q
544 passed, 2324 subtests passed in 635.71s (0:10:35)
0 failed
```

Son 22 pruebas más que las 522 del cierre anterior y ninguna prueba eliminada.
Las nuevas pruebas parametrizan nombres arbitrarios, tres niveles, duplicados,
`Backup`, `Releases`, carpeta vacía, carpeta no compatible, recursividad,
preservación de hermanos, estado actual y escape de raíz.

La validación real, separada de pytest, confirmó seis ramas, profundidad máxima
6, búsquedas léxicas/semánticas y preservación mediante IDs y hashes. OAuth
permaneció en `drive.readonly` y no se guardó contenido.
