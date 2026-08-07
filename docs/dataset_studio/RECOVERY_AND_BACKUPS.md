# Recuperación y copias

## Guardado seguro

Cada autosave:

1. comprueba que el archivo no cambió externamente;
2. copia el metadato actual a `snapshots`;
3. registra `recovery.json`;
4. escribe y sincroniza un temporal en el mismo volumen;
5. reemplaza atómicamente el destino, con reintentos breves para bloqueos transitorios de Windows;
6. elimina el diario al completar.

Se conservan cinco snapshots por defecto. La cantidad es configurable en el proyecto.

## Fallos

- **Cierre inesperado**: el diario indica una operación incompleta; el archivo original o el último snapshot siguen disponibles.
- **CSV/JSONL corrupto**: la apertura se detiene con línea o campos afectados; no se intenta reparar sobre el original.
- **Snapshot dañado**: la recuperación recorre snapshots recientes hasta encontrar uno que pueda validarse.
- **Cambio externo**: se bloquea el guardado para evitar sobrescritura.
- **Lock huérfano**: solo se retira si ha caducado y el proceso ya no existe.
- **Segunda instancia**: se rechaza escritura; el modo lectura no crea ni elimina locks.

Las copias están en `%LOCALAPPDATA%\AtlasDatasetStudio\projects\<id>`. Para una recuperación manual, cierre todas las instancias, copie el metadato actual a un lugar seguro y reemplace únicamente con un snapshot validado.
