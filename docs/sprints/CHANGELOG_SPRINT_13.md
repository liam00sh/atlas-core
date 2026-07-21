# Changelog exacto — Sprint 13

## Archivos creados

- `memory/workflow/__init__.py`
- `memory/workflow/models.py`
- `memory/workflow/detector.py`
- `memory/workflow/store.py`
- `memory/workflow/audit.py`
- `memory/workflow/service.py`
- `memory/workflow/conversation.py`
- `tools/memory_write.py`
- `tests/memory/test_controlled_workflow.py`
- `tests/memory/test_workflow_conversation.py`
- `tests/tools/test_memory_workflow_tool.py`
- `docs/sprints/SPRINT_13_CONTROLLED_CONVERSATIONAL_MEMORY.md`
- `docs/sprints/CHANGELOG_SPRINT_13.md`
- `INSTRUCCIONES_SPRINT_13.md`
- `docs/sprints/TEST_RESULTS_SPRINT_13.md`

## Archivos modificados

- `.gitignore`: excluye el estado personal de `data/memory_workflow/`.
- `memory/memory_manager.py`: ruta inyectable para pruebas, escritura atómica y CRUD compatible por propietario con metadatos.
- `tools/atlas_adapter.py`: permisos de memoria solo para usuarios estructurados; nunca concede permiso sensible automáticamente.
- `core/atlas.py`: registra servicio, controlador y herramienta; antepone el ciclo confirmable al guardado heredado y enmascara secretos en logs.
- `core/atlas_memory.py`: añade el punto de integración conversacional sin eliminar la API heredada.
- `tests/tools/test_atlas_framework_integration.py`: verifica el registro conjunto con el sistema heredado.
- `tests/tools/test_atlas_tool_adapter.py`: verifica permisos de usuario, visitante y ausencia del permiso sensible implícito.

## Capacidades

`memory.propose`, `memory.confirm`, `memory.reject`, `memory.update_proposal`, `memory.propose_update`, `memory.confirm_update`, `memory.propose_delete`, `memory.select_delete`, `memory.confirm_delete`, `memory.read` y `memory.audit.read`.

## Permisos

`memory.read`, `memory.sensitive.read`, `memory.propose`, `memory.write`, `memory.update`, `memory.delete`, `memory.sensitive.write` y `memory.audit.read`.

## Correcciones y compatibilidad

- Ninguna detección escribe memoria.
- Confirmación idempotente, aislamiento por usuario/sesión y caducidad.
- Estado recuperable `processing` y reconciliación mediante `proposal_id`.
- Selección conversacional completa cuando un borrado tiene varios resultados.
- Procedencia ligada a los últimos recuerdos mostrados por usuario y sesión.
- Lectura general con exclusión de recuerdos sensibles heredados.
- Relaciones encaminadas al motor estructurado.
- Persistencia auxiliar atómica y auditoría minimizada.
- Se conservan `self.tool_registry`, `self.tool_selector`, `self.framework_tool_registry`, `self.tool_manager` y `self.framework_tool_adapter`.
- No se modifica `main.py`, Drive, RAG, índices documentales ni contratos públicos anteriores.
