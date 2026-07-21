# Sprint 1 — Núcleo del Atlas Tools Framework

## Estado

**Completado y validado.**

## Objetivo

Crear el núcleo independiente del nuevo sistema de herramientas de Atlas sin modificar ni sustituir el sistema actual implementado en `core/atlas_tools.py`.

## Alcance implementado

El Sprint 1 incorpora:

- `BaseTool`
- `Capability`
- `ToolContext`
- `ToolResult`
- `ToolRegistry`
- `ToolManager`
- excepciones específicas del framework
- `SystemStatusTool` como herramienta real de prueba
- pruebas unitarias del registro, permisos, estado y ejecución

## Estructura creada

```text
atlas_core/
├── tools/
│   ├── __init__.py
│   ├── base_tool.py
│   ├── capability.py
│   ├── context.py
│   ├── exceptions.py
│   ├── manager.py
│   ├── registry.py
│   ├── result.py
│   └── system_status.py
└── tests/
    └── tools/
        ├── test_manager.py
        └── test_registry.py
```

## Decisiones técnicas

1. El framework nuevo permanece desacoplado del núcleo.
2. `core/atlas_tools.py` no se elimina ni se sustituye.
3. El registro antiguo y el nuevo convivirán durante la migración.
4. Las herramientas declaran capacidades y permisos.
5. Todas las ejecuciones devuelven `ToolResult`.
6. `ToolManager` centraliza resolución, permisos, ejecución y auditoría.
7. La integración con `core/atlas.py` queda reservada para el Sprint 2.

## Validación

Comando ejecutado:

```bash
python -m pytest tests/tools -q
```

Resultado esperado y confirmado:

```text
5 passed
```

## Qué desbloquea

El Sprint 1 permite que el Sprint 2 conecte el framework a la clase `Atlas` de forma segura, manteniendo intacto el sistema de herramientas actual.
