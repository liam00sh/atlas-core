# Sprint 9 — Índice documental persistente de Google Drive

## Objetivo

Evitar que Atlas tenga que releer varios documentos de Drive en cada consulta.

## Nuevo componente

```text
tools/google_drive_index.py
```

Contiene:

- `GoogleDriveDocumentIndex`
- `GoogleDriveIndexTool`
- `IndexedDocument`
- `IndexedChunk`
- `IndexSearchMatch`

## Capacidades

```text
documents.index.sync
documents.index.search
documents.index.status
documents.index.clear
```

## Persistencia

El índice se guarda en:

```text
data/integrations/google_drive/document_index.json
```

Es un dato derivado y reconstruible. No pertenece a la memoria personal y no
modifica ningún archivo de Google Drive.

## Sincronización incremental

Atlas compara el `modified_time` de cada documento con el índice existente.

- Los documentos sin cambios no se descargan de nuevo.
- Los documentos nuevos se indexan.
- Los modificados se vuelven a leer.
- Los eliminados desaparecen del índice.
- Los archivos sin contenido textual se omiten de forma segura.

## Uso conversacional

```text
Actualiza el índice de Drive
Estado del índice de Drive
Busca Ollama en el índice de Drive
Borra el índice de Drive
```

Los resultados del índice conservan el nombre, identificador y enlace de la
fuente, y pueden abrirse después mediante `Abre el primero`.

## Seguridad

- Google Drive sigue siendo solo lectura.
- El índice solo contiene texto recuperado mediante la integración autorizada.
- `credentials.json` y `token.json` no se recorren desde Drive.
- El índice puede borrarse sin afectar a Drive.
- La herramienta exige `google.drive.read`.
