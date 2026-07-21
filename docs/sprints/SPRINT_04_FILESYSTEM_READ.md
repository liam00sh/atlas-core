# Sprint 4 — Lectura segura del sistema de archivos

## Estado

Preparado para instalación y validación.

## Objetivo

Añadir la primera herramienta funcional del nuevo Atlas Tools Framework:

```text
filesystem.read
```

Permite leer archivos de texto dentro de `atlas_core`, mediante el adaptador y
el `ToolManager`, sin dar acceso libre al resto del equipo.

## Seguridad

La herramienta aplica estas protecciones:

- raíz autorizada explícita;
- normalización y resolución de la ruta real;
- bloqueo de recorridos mediante `..`;
- bloqueo de enlaces simbólicos que salgan de la raíz;
- rechazo de directorios;
- rechazo de archivos binarios;
- tamaño máximo de 1 MB;
- truncado configurable del contenido;
- bloqueo de nombres habituales de credenciales;
- bloqueo de extensiones de claves y certificados;
- permiso obligatorio `filesystem.read`.

La raíz se calcula mediante:

```python
Path(__file__).resolve().parent.parent
```

Por tanto, no depende del directorio desde el que se ejecute `python main.py`.

## Integración

Atlas registra ahora dos herramientas en el framework:

```text
system.status
filesystem.read
```

El adaptador añade a su lista segura:

```text
filesystem.read
```

La herramienta puede ejecutarse internamente con:

```python
atlas.execute_framework_tool(
    "filesystem.read",
    arguments={"path": "README.md"},
)
```

## Alcance

El Sprint no conecta aún `filesystem.read` al lenguaje natural. El usuario no
puede activarla automáticamente escribiendo «lee este archivo». Esa selección
controlada se abordará en el siguiente Sprint.

## Qué desbloquea

El Sprint 5 podrá incorporar selección determinista para un conjunto muy
limitado de solicitudes, o ampliar el framework con operaciones de listado y
metadatos antes de habilitar la selección conversacional.
