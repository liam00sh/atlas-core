# Sprint 3 — Adaptador Atlas ↔ ToolManager

## Estado

Preparado para instalación y validación.

## Objetivo

Crear una frontera explícita entre `AtlasToolsMixin` y el nuevo
`ToolManager`, sin desviar todavía la conversación ni migrar las herramientas
heredadas.

## Nuevo componente

```text
tools/atlas_adapter.py
```

`AtlasToolAdapter` tiene tres responsabilidades:

1. Construir un `ToolContext` seguro a partir del estado de Atlas.
2. Resolver los permisos que se entregan al nuevo framework.
3. Convertir errores controlados del framework en `ToolResult`.

## Política inicial de permisos

El adaptador no concede automáticamente el permiso solicitado. Durante este
Sprint solo existe una lista explícita de permisos de lectura seguros:

```text
system.status.read
```

Si la capacidad general `tools` está desactivada, el contexto no recibe
permisos y la ejecución se bloquea.

## Integración con Atlas

`core/atlas.py` inicializa:

```python
self.framework_tool_adapter = AtlasToolAdapter(
    self.tool_manager
)
```

`AtlasToolsMixin` incorpora:

```python
build_framework_tool_context(...)
execute_framework_tool(...)
get_framework_tool_count()
```

Estos métodos son APIs internas. `_handle_tool()` continúa utilizando el
registro y el selector heredados.

## Garantías

- No cambia el orden de `Atlas.process()`.
- No se migra ninguna herramienta antigua.
- No se modifica el sistema de confirmaciones.
- No se interpreta lenguaje natural con el nuevo framework.
- No se concede Internet.
- Los permisos son explícitos y mínimos.

## Qué desbloquea

El Sprint 4 podrá incorporar una primera herramienta útil al nuevo framework
y ejecutarla mediante esta frontera común, sin acoplarla directamente a Atlas.
