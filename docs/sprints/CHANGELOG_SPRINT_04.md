# Entrada de Changelog — Sprint 4

## Fase 4 — Sprint 4: primera herramienta funcional

- Creada `FilesystemReadTool`.
- Añadida la capacidad `filesystem.read`.
- Limitada la lectura a la raíz de `atlas_core`.
- Bloqueados recorridos de ruta y escapes mediante enlaces simbólicos.
- Bloqueados archivos sensibles, binarios y excesivamente grandes.
- Añadido truncado seguro del contenido.
- Añadido el permiso explícito `filesystem.read`.
- Registrada la herramienta durante la inicialización de Atlas.
- Actualizado `AtlasToolAdapter` con el nuevo permiso seguro.
- Añadidas siete pruebas unitarias de seguridad y lectura.
- Añadidas dos pruebas de integración con Atlas.
- Conservado sin cambios el flujo conversacional heredado.
