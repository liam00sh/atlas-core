# Resultados de Drive — ampliación del Sprint 17

Fecha: 19 de julio de 2026. Cliente OAuth y Ollama locales reales, raíz
`Atlas Project`, alcance `drive.readonly`, índices temporales.

## Comparación

Durante la implementación se añadieron siete archivos indexables a la carpeta
sincronizada, por lo que la primera pasada anterior y posterior no tienen un
conjunto idéntico. Se muestran con esa advertencia y las conclusiones se basan
principalmente en escenarios sin cambios y contadores remotos.

| Métrica | Antes | Después | Mejora | Observaciones |
|---|---:|---:|---:|---|
| Global inicial | 287,756 s / 336 descargas | 266,360 s / 343 descargas | 7,4 % indicativo | La carga posterior tenía 7 archivos más; no es comparación controlada |
| Global sin cambios | 21,983 s / 8 descargas | 18,409 s / 0 descargas | 16,3 % y 8 descargas evitadas | Los vacíos se recuerdan por revisión |
| `00 - Documentación` inicial | 19,032 s / 21 descargas | 18,637 s / 21 descargas | 2,1 % | Misma cantidad de documentos |
| `00 - Documentación` incremental | no disponible | 0,370 s / 0 descargas | 98,0 % frente al global posterior sin cambios | Un listado remoto |
| `04 - Python` inicial | 220,371 s / 303 descargas | 205,033 s / 310 descargas | 7,0 % indicativo | La rama posterior tenía 7 archivos más |
| `04 - Python` incremental | no disponible | 14,050 s / 0 descargas | 23,7 % frente al global posterior sin cambios | 44 carpetas; la rama contiene casi todo el índice |
| Archivo individual ya indexado | 0,496 s / 1 descarga | 0,071 s / 0 descargas | 85,7 % | Una lectura de metadatos |
| Árbol estructural inicial | no disponible | 18,234 s / 61 listados | nueva capacidad | 456 nodos, sin contenido |
| Árbol estructural con TTL | no disponible | 0,011 s / 0 listados | 99,94 % frente al primer árbol | Caché aislada por usuario/cuenta/raíz |
| 500 embeddings iniciales | 85,273 s | 78,709 s | 7,7 % indicativo | Variación normal de Ollama |
| 500 embeddings sin cambios | 0,339 s / 0 nuevos | 0,375 s / 0 nuevos | sin mejora temporal | Se reutilizaron los 500 en ambos casos |

## Trabajo evitado

- Segunda actualización global: 8 descargas evitadas.
- `00 - Documentación` después del global: 322 archivos no comprobados como
  documentos y 343 descargas evitadas respecto a reconstruir la raíz.
- Archivo individual: 342 archivos fuera del objetivo y una descarga evitada.
- Árbol dentro del TTL: 61 llamadas de listado evitadas.
- Segunda sincronización semántica: 500 embeddings reutilizados, 0 generados.

## Interpretación

La ampliación no pretende acelerar artificialmente una primera descarga global.
La mejora principal es evitarla cuando el usuario conoce su ámbito. La rama
`00 - Documentación` pasa de una operación global de 266,360 segundos a una
actualización incremental de 0,370 segundos sin cambios. `04 - Python` obtiene
menos ventaja porque contiene la mayoría del repositorio, pero evita todas las
descargas.

## Integridad del benchmark

Los datos completos están en `data/performance/drive_results_sprint17.json`,
ruta ignorada por Git. No contiene documentos ni credenciales. No se indujeron
cambios remotos; renombrados, movimientos, eliminaciones y errores se validan
mediante pruebas automáticas.

## Validación transversal de todas las ramas de Atlas Project

| Ámbito real | ID anónimo | Profundidad | Archivos totales | Indexables | No indexables | Fragmentos | Embeddings reutilizados | Eliminados | Errores |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atlas Project | `dfb519084c4c` | 0 | 367 | 351 | 16 | 2.745 | 2.745 | 0 | 0 |
| 01 - Raspberry | `d51430d68eda` | 1 | 12 | 7 | 5 | 7 | 7 | 0 | 0 |
| 02 - PC | `d83caea4d1a1` | 1 | 6 | 3 | 3 | 3 | 3 | 0 | 0 |
| 04 - Python | `73b110fb57dd` | 1 | 321 | 315 | 6 | 2.203 | 2.203 | 0 | 0 |
| 11 - Backups | `0183d8b237c3` | 1 | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| Releases | `c5ef8d507cea` | 1 | 3 | 3 | 0 | 9 | 9 | 0 | 0 |

El árbol real tuvo 466 entradas, 99 carpetas, 367 archivos y profundidad máxima
6. La construcción estructural tardó 20,548 segundos. El índice global produjo
343 documentos y 2.745 fragmentos en 263,034 segundos; Ollama generó 2.745
embeddings en 432,652 segundos. Las pasadas de rama reutilizaron sus vectores.

Se verificaron además:

- segundo nivel: 3 documentos, 3 embeddings reutilizados;
- carpeta profunda de nivel 5: 2 documentos y sus hermanos intactos;
- carpeta vacía: 0 documentos, 0 errores;
- carpeta indexable: 5 documentos y 27 fragmentos;
- carpeta no indexable: 5 archivos visibles, 0 descargas;
- archivo individual fuera de `00` y `04`: 0 descargas, una lectura de
  metadatos, 0 eliminaciones.

La primera instrumentación calculó `pwd_matches` después de volver a la raíz.
Una comprobación real suplementaria repitió `cd` y `pwd` y obtuvo `true` para
las seis rutas. La medición también reveló ocho redescargas de archivos vacíos
en `04 - Python` después de una pasada no recursiva de la raíz; se corrigió el
estado auxiliar y se añadió una prueba automática específica.

La prueba de preservación comparó exclusivamente IDs y SHA-256: `02 - PC`,
`11 - Backups` y una carpeta profunda no alteraron ninguna rama hermana.
