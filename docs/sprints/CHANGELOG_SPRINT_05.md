# Entrada de Changelog — Sprint 5

## Fase 4 — Sprint 5: Google Drive Reader

- Creado el contrato `GoogleDriveClient`.
- Creado `GoogleDriveReadTool`.
- Añadidas las capacidades `documents.search`, `documents.read` y `folders.list`.
- Añadido el permiso único `google.drive.read`.
- Limitada la integración a operaciones de solo lectura.
- Creado `UnavailableGoogleDriveClient`.
- Creado `InMemoryGoogleDriveClient` para pruebas.
- Registrada la herramienta desactivada durante el arranque de Atlas.
- Añadido `configure_google_drive_client()` al mixin de herramientas.
- Añadidas ocho pruebas unitarias.
- Añadidas dos pruebas de integración.
- Mantenida la independencia del Core respecto al SDK de Google.
