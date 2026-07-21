# Entrada de Changelog — Sprint 6

## Fase 4 — Sprint 6: OAuth real de Google Drive

- Creado `GoogleDriveOAuthConfig`.
- Creado `GoogleDriveOAuthProvider`.
- Creado `GoogleDriveApiClient`.
- Añadido OAuth para aplicación de escritorio.
- Añadido el alcance exclusivo `drive.readonly`.
- Añadida renovación automática del token.
- Añadido almacenamiento local protegido del token.
- Añadida carga no interactiva durante el arranque.
- Añadida restricción opcional por carpeta raíz.
- Añadida exportación textual de Docs, Sheets y Slides.
- Añadida lectura de archivos de texto subidos.
- Rechazados formatos binarios.
- Añadido script de autorización.
- Añadido archivo de dependencias opcionales.
- Excluidas credenciales y tokens mediante `.gitignore`.
- Añadidas nueve pruebas unitarias.
- Añadidas dos pruebas de integración.
