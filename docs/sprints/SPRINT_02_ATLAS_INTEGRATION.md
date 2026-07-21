# Sprint 2 — Integración segura con Atlas Core

## Estado

Preparado para instalación y validación en el proyecto real.

## Objetivo

Inicializar el nuevo Atlas Tools Framework dentro de la clase `Atlas` sin
reemplazar ni alterar el funcionamiento del sistema de herramientas heredado.

## Cambios realizados

### `core/atlas.py`

El registro actual pasa a importarse con un alias explícito:

```python
from ai.tools.tool_registry import ToolRegistry as LegacyToolRegistry
```

Se añaden los componentes del nuevo framework:

```python
from tools.manager import ToolManager
from tools.registry import ToolRegistry as FrameworkToolRegistry
from tools.system_status import SystemStatusTool
```

Atlas conserva:

```python
self.tool_registry
self.tool_selector
```

Y añade:

```python
self.framework_tool_registry
self.tool_manager
```

La primera herramienta registrada en el nuevo framework es:

```text
system.status
└── system.status.read
```

## Garantías de compatibilidad

- No se modifica `core/atlas_tools.py`.
- No se modifica `main.py`.
- No se modifica `Atlas.process()`.
- El sistema heredado continúa usando `self.tool_registry`.
- El nuevo framework utiliza `self.framework_tool_registry`.
- Ninguna petición del usuario se desvía todavía al nuevo framework.
- La migración sigue siendo reversible.

## Pruebas añadidas

`tests/tools/test_atlas_framework_integration.py` comprueba:

1. Que ambos sistemas se inicializan.
2. Que `ToolManager` utiliza el nuevo registro.
3. Que `SystemStatusTool` queda registrada.
4. Que la capacidad `system.status.read` puede ejecutarse con permiso.

## Qué desbloquea

El Sprint 3 podrá crear un adaptador controlado entre el flujo real de Atlas y
`ToolManager`, sin tener que modificar todavía las herramientas heredadas.
