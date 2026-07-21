# Sprint 7 — Google Drive conversacional

## Objetivo

Conectar la entrada conversacional de Atlas con la herramienta real de Google
Drive ya autorizada en el Sprint 6.

## Alcance

Atlas puede interpretar de forma determinista:

```text
Busca en Drive Constitución de Atlas
Busca el documento Manual de pruebas en Drive
Lista Google Drive
Lee el documento Constitución de Atlas
Abre el primero
Lee el 2
```

## Flujo

```text
Usuario
  ↓
Atlas.process()
  ↓
GoogleDriveConversationController
  ↓
AtlasToolAdapter
  ↓
ToolManager
  ↓
GoogleDriveReadTool
  ↓
GoogleDriveApiClient
```

La IA no selecciona ni ejecuta la herramienta.

## Seguridad

El controlador solo intercepta peticiones explícitas relacionadas con Drive.
Una frase genérica como:

```text
Busca información sobre Python
```

continúa por el flujo normal de Atlas.

Las capacidades siguen siendo exclusivamente:

```text
documents.search
documents.read
folders.list
```

y continúan protegidas mediante:

```text
google.drive.read
```

## Estado conversacional

Se conserva temporalmente y por usuario:

- últimos resultados;
- última búsqueda;
- documento abierto.

Esto permite responder:

```text
Abre el primero
```

sin mezclar resultados entre Liam, Saray u otros usuarios.

## Límites de este Sprint

- La búsqueda se realiza por nombre de archivo.
- Se muestran hasta 10 resultados.
- La lectura presenta una vista previa de hasta 4000 caracteres.
- Todavía no se resume el documento automáticamente.
- Todavía no se buscan palabras dentro de todos los documentos.

Estas funciones podrán añadirse posteriormente sin modificar OAuth.
