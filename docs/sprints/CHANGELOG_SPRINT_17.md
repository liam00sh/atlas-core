# Changelog — Sprint 17

## Archivos creados

- `scripts/benchmark_sprint17.py`
- `tests/performance/test_sprint17_identity_cache.py`
- `docs/sprints/performance_baseline_sprint17.json`
- `docs/sprints/performance_candidate_sprint17.json`
- `docs/sprints/performance_results_sprint17.json`
- `docs/sprints/SPRINT_17_SAFE_PERFORMANCE_OPTIMIZATION.md`
- `docs/sprints/PERFORMANCE_BASELINE_SPRINT_17.md`
- `docs/sprints/PERFORMANCE_RESULTS_SPRINT_17.md`
- `docs/sprints/CHANGELOG_SPRINT_17.md`
- `docs/sprints/TEST_RESULTS_SPRINT_17.md`
- `INSTRUCCIONES_SPRINT_17.md`

## Archivos modificados

- `identity/identity_storage.py`: caché local de tres colecciones con firma e invalidación.
- `identity/family_initializer.py`: comprobación idempotente en un único snapshot.

No se modificó `main.py` ni se eliminaron componentes heredados.

## Ampliación: Drive por ámbitos

### Archivos creados

- `tools/google_drive_structure.py`
- `scripts/benchmark_drive_scoped_sprint17.py`
- `tests/tools/test_google_drive_structure.py`
- `tests/tools/test_google_drive_structure_tool.py`
- `tests/tools/test_google_drive_scoped_index.py`
- `tests/tools/test_google_drive_scoped_conversation.py`
- `docs/sprints/SPRINT_17_DRIVE_SCOPED_INDEXING.md`
- `docs/sprints/DRIVE_INDEX_BASELINE_SPRINT_17.md`
- `docs/sprints/DRIVE_INDEX_RESULTS_SPRINT_17.md`

### Archivos modificados

- `.gitignore`: excluye índices reales y resultados locales de rendimiento.
- `core/atlas.py`: registra árbol y navegación en el framework nuevo.
- `core/atlas_tools.py`: sustituye de forma compatible el cliente provisional
  de la herramienta estructural al restaurar OAuth.
- `knowledge/retriever.py`, `knowledge/service.py`, `knowledge/sources.py` y
  `tools/knowledge.py`: propagan ámbitos documentales opcionales.
- `tools/__init__.py`: exporta los contratos estructurales.
- `tools/google_drive.py` y `tools/google_drive_oauth.py`: lectura segura de
  metadatos de un elemento por ID.
- `tools/google_drive_index.py`: sincronización global compatible y parcial no
  destructiva, procedencia, estados vacíos, ámbitos y detección de movimientos.
- `tools/google_drive_semantic.py`: búsqueda y sincronización semántica por
  ámbito con reutilización de vectores.
- `tools/google_drive_rag.py`: recuperación RAG limitada antes del ranking.
- `tools/google_drive_conversation.py`: navegación y actualización/búsqueda
  local mediante intención determinista y estado por sesión.
- `tests/tools/test_google_drive_semantic.py`: cobertura de ámbito, metadatos y
  preservación de otras ramas.
- `tests/knowledge/test_knowledge_core.py`: contrato de propagación del ámbito.
- `docs/sprints/CHANGELOG_SPRINT_17.md`
- `docs/sprints/TEST_RESULTS_SPRINT_17.md`
- `INSTRUCCIONES_SPRINT_17.md`

### Capacidades añadidas

- `drive.structure.sync`, `drive.pwd`, `drive.cd`, `drive.list`, `drive.tree`
  y `drive.resolve_path`.
- `documents.index.sync_scope`.
- Ámbitos `global`, `root`, `subtree`, `current` y `file` para recuperación.

El permiso sigue siendo `google.drive.read`; no se añadieron permisos de
escritura ni se cambió el alcance OAuth. El comando global y las capacidades
anteriores permanecen disponibles.

## Cierre de validación transversal

### Archivos creados

- `scripts/validate_drive_branches_sprint17.py`
- `tests/tools/test_google_drive_generic_scopes.py`

### Archivos modificados

- `tools/google_drive_index.py`: elimina la exclusión injustificada de
  `Releases`, permite configurar carpetas excluidas y conserva la procedencia
  de estados vacíos durante actualizaciones parciales.
- `tools/google_drive_structure.py`: elimina `Releases` de la poda, hace
  configurable la política y registra estado/motivo de los nodos excluidos.
- `tools/google_drive_conversation.py`: variantes genéricas de árbol,
  actualización recursiva/no recursiva y búsqueda desde aquí/global.
- `tests/tools/test_google_drive_scoped_index.py`: regresión de estados vacíos
  anidados.
- `tests/tools/test_google_drive_scoped_conversation.py`: frases con `02`,
  `11` y nombres arbitrarios sin lógica productiva especial.
- `docs/sprints/SPRINT_17_DRIVE_SCOPED_INDEXING.md`
- `docs/sprints/DRIVE_INDEX_RESULTS_SPRINT_17.md`
- `docs/sprints/TEST_RESULTS_SPRINT_17.md`
- `docs/sprints/CHANGELOG_SPRINT_17.md`
- `INSTRUCCIONES_SPRINT_17.md`

La validación real usó índices temporales y OAuth de solo lectura. El resultado
detallado local está en
`data/performance/drive_cross_branch_validation_sprint17.json`, ignorado por
Git y sin contenido documental.
