# Resultados de rendimiento — Sprint 17

| Métrica | Antes | Después | Mejora | Observaciones |
|---|---:|---:|---:|---|
| Arranque Atlas | 37.216 s | 2.843 s | 92.4 % | Mismo constructor y proveedor desactivado |
| CPU de arranque | 25.391 s | 1.828 s | 92.8 % | Medición extendida final |
| FamilyInitializer | 34.061 s | 0.686 s | 98.0 % | Omite comprobaciones completas ya satisfechas |
| Lecturas JSON comparables | 1469 | 13 | 99.1 % | El escenario extendido final realiza 17 por una consulta adicional |
| Pico de RAM | 19.41 MB | 19.52 MB | -0.6 % | Incremento aproximado de 0.11 MB, aceptado |
| Saludo inicial | 60.487 ms | 32.641 ms | 46.0 % | Variación de máquina incluida |
| Memoria inicial | 77.615 ms | 51.659 ms | 33.4 % | Misma consulta y límites |
| KnowledgeRetriever inicial | 72.730 ms | 32.599 ms | 55.2 % | Mismas fuentes y prioridades |
| Herramienta inicial | 171.340 ms | 127.598 ms | 25.5 % | Misma capacidad y permisos |
| Herramienta repetida | 7.958 ms | 1.489 ms | 81.3 % | Sin caché de resultados personales |
| Suite completa | 953.65 s | 636.40 s | 33.3 % | Aumentó de 480 a 484 pruebas |

## Proveedor local y contexto

La ruta simulada de proveedor local tardó 67.169 ms sin incluir inferencia real. Registró exactamente:

- 1 llamada a disponibilidad;
- 1 llamada a generación;
- prompt de 406 caracteres.

No se detectaron llamadas duplicadas. La latencia de inferencia real de Ollama depende del modelo y hardware y no se mezcló con la optimización interna.

## Costes restantes

La carga OAuth de Google consume aproximadamente 1.6 s en arranque frío. Se decidió no diferirla porque actualmente Atlas restaura la sesión de Drive al arrancar; moverla cambiaría estado y latencia de la primera consulta. Las pruebas que construyen desde cero todo el árbol familiar continúan siendo costosas porque realizan escrituras reales necesarias.

Evidencia cruda: `performance_results_sprint17.json`. `performance_candidate_sprint17.json` conserva la medición intermedia de la caché aislada.

