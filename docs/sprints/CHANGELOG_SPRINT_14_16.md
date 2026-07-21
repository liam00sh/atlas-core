# Changelog — Sprints 14 a 16

## Creados

- `memory/semantic_index.py`
- `memory/links.py`
- `memory/long_term.py`
- `tests/memory/test_semantic_links_long_term.py`
- `docs/sprints/SPRINT_14_PERSONAL_SEMANTIC_MEMORY.md`
- `docs/sprints/SPRINT_15_MEMORY_RELATIONSHIPS.md`
- `docs/sprints/SPRINT_16_LONG_TERM_MEMORY.md`
- `docs/sprints/CHANGELOG_SPRINT_14_16.md`
- `docs/sprints/TEST_RESULTS_SPRINT_14_16.md`

## Modificados

- `memory/memory_manager.py`: eventos derivados y metadatos de largo plazo.
- `memory/memory_retriever.py`: frecuencia y última consulta.
- `knowledge/sources.py`: fuentes semántica personal y contextual.
- `knowledge/retriever.py`: prioridades de las fuentes nuevas.
- `core/atlas.py`: composición de los tres servicios sin cambiar registros de herramientas.
- `.gitignore`: exclusión de índices personales bajo `data/knowledge/`.

No se modifica `main.py`, Drive, el índice semántico documental ni los contratos de los dos frameworks de herramientas.
