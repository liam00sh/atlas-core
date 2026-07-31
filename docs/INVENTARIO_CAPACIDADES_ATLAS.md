# Inventario verificable de capacidades de Atlas

## Fuente de verdad

El inventario ejecutable se obtiene con
`console.command_help.inventory_records()`. Combina:

- los módulos descubiertos dinámicamente en `commands/` mediante `COMMANDS`;
- `CONVERSATIONAL_ENTRIES`, para rutas reales del núcleo que no son módulos de
  comando;
- `SERVICE_ENTRIES`, para servicios conversacionales y capacidades por canal.

Ayuda, búsqueda y recomendaciones consumen `all_entries()` después de aplicar
el mismo `HelpAccessContext`. No mantienen listas de visibilidad separadas.

Cada registro expone nombre canónico, aliases, categoría, descripción,
ejemplos, capacidad requerida, exclusividad del propietario, canales,
presencia, carácter informativo, ejecución de acción y estado de
implementación.

## Resultado del inventario

Se detectan 69 capacidades de usuario: 10 comandos dinámicos, 40 rutas
conversacionales y 19 servicios catalogados. Hay 68 implementadas y una
preparada pero todavía no anunciada como ejecutable: recuperación controlada.

| Grupo | Capacidades principales | Estado |
| --- | --- | --- |
| General y sistema | ayuda, saludo, fecha, versión, información, estado, salir | Implementado |
| Usuarios | invitado temporal, crear/listar/cambiar perfil, quién soy | Implementado; alta reservada al propietario |
| Telegram | `/start`, confirmación, estado, ayuda vinculada, adjuntos seguros | Implementado; análisis avanzado opcional |
| Comunicación | mensajes entre perfiles vinculados | Implementado |
| Memoria | guardar, consultar, corregir, olvidar y exportar | Implementado |
| Organización | agenda, recordatorios, listas, rutinas y objetos | Implementado |
| Hogar | luces, oxígeno, grupos, horarios y temporizadores | Implementado; permiso y presencia efectivos |
| Identidad | Daxter, Coco y modos | Implementado |
| Clima e Internet | tiempo, búsqueda, fuentes y comparación | Implementado; proveedores simulables |
| Drive | buscar, leer, buscar contenido y sincronizar índice | Implementado; sincronización restringida |
| Windows | sistema, disco, procesos y apertura catalogada | Implementado; abrir solo PC/CLI |
| Monitorización | estado uniforme e incidencias | Implementado |
| Recuperación | recomendación, autorización y auditoría | Preparado; sin ejecución automática ni consumidor conversacional final |

## Capacidades internas

Los registros de `tools/` y los catálogos `automation/stage_*_catalog.py`
contienen capacidades de bajo nivel como `documents.*`, `drive.*`,
`knowledge.*`, `memory.*`, `home.*`, `windows.*`, `backup.*` y
`service.*`. Se conservan como APIs internas y solo se muestran en ayuda cuando
existe una ruta de usuario real. Un identificador técnico no se presenta como
comando inventado.

## Reglas de mantenimiento

1. Un nuevo módulo de `commands/` debe declarar metadatos en `COMMAND`.
2. Una ruta conversacional nueva debe añadir una sola entrada al catálogo
   central, no listas separadas para ayuda y búsqueda.
3. Las pruebas verifican ausencia de duplicados y presencia de todos los campos.
4. `implementation_status=prepared` o `partial` nunca equivale a ejecutable.
5. Los filtros de propietario, permiso, canal y presencia se aplican antes de
   cualquier coincidencia aproximada o por intención.
