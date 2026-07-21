# Entrada de Changelog — Sprint 2

## Fase 4 — Sprint 2: integración del Tools Framework con Atlas Core

- Renombrada mediante alias la importación del registro heredado.
- Mantenidos intactos `self.tool_registry` y `self.tool_selector`.
- Inicializado `self.framework_tool_registry`.
- Registrada `SystemStatusTool`.
- Inicializado `self.tool_manager`.
- Añadidas pruebas de convivencia entre ambos sistemas.
- Conservado sin cambios el flujo de `Atlas.process()`.
- Conservado sin cambios `core/atlas_tools.py`.
- Preparada la base para el adaptador del Sprint 3.
