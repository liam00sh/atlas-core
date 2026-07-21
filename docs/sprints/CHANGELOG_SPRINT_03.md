# Entrada de Changelog — Sprint 3

## Fase 4 — Sprint 3: adaptador entre Atlas y ToolManager

- Creado `AtlasToolAdapter`.
- Definido el contrato mínimo `AtlasLike`.
- Añadida construcción segura de `ToolContext`.
- Añadida una política inicial de permisos de lectura.
- Bloqueada la ejecución cuando la capacidad general de herramientas está desactivada.
- Convertidos los errores controlados del framework en `ToolResult`.
- Inicializado `framework_tool_adapter` en la clase `Atlas`.
- Añadidos métodos internos de ejecución al `AtlasToolsMixin`.
- Mantenido intacto `_handle_tool()` y el flujo conversacional heredado.
- Añadidas cuatro pruebas del adaptador y de su integración.
