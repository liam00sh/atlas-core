# Sprint 5 — Google Drive Reader

## Objetivo

Incorporar Google Drive al nuevo Tools Framework siguiendo el modelo de
seguridad oficial de Atlas:

- solo lectura;
- permisos explícitos;
- alcance desacoplado;
- funcionamiento del Core aunque Drive no esté configurado;
- ninguna dependencia directa del núcleo respecto al SDK de Google.

## Capacidades

```text
documents.search
documents.read
folders.list
```

Todas exigen:

```text
google.drive.read
```

## Arquitectura

```text
Atlas
  ↓
AtlasToolAdapter
  ↓
ToolManager
  ↓
GoogleDriveReadTool
  ↓
GoogleDriveClient
  ↓
Proveedor real futuro
```

`GoogleDriveClient` es un protocolo neutral. La herramienta no conoce OAuth,
la API de Google ni dónde se almacenan los tokens.

## Estado al arrancar

Atlas registra `GoogleDriveReadTool` con
`UnavailableGoogleDriveClient`. Como no hay credenciales configuradas, la
herramienta queda desactivada automáticamente.

Esto garantiza que:

- Atlas inicia normalmente;
- Drive no se consulta por accidente;
- no se solicitan credenciales durante el arranque;
- el Core no depende de Internet;
- la integración puede configurarse después.

## Configuración

`AtlasToolsMixin` incorpora:

```python
configure_google_drive_client(client)
```

La capa de autenticación futura creará un cliente real y lo inyectará mediante
ese método.

## Cliente de pruebas

`InMemoryGoogleDriveClient` permite validar toda la herramienta sin red,
cuentas ni credenciales.

## Seguridad

No se implementan capacidades de escritura, creación, eliminación, movimiento,
compartición ni modificación. La integración comienza exclusivamente en modo
lectura, tal como establece el modelo de seguridad de Atlas.

## Siguiente paso

El Sprint 6 podrá implementar el proveedor real basado en la API de Google y
su configuración OAuth, manteniendo intacta la herramienta y el Core.
