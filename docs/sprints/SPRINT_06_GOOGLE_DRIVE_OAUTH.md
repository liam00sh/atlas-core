# Sprint 6 — Proveedor OAuth real de Google Drive

## Objetivo

Implementar la conexión real con Google Drive mediante OAuth 2.0 y Drive API
v3, sin introducir secretos en el código y sin impedir que Atlas arranque
cuando la integración no esté disponible.

## Dependencias opcionales

```text
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

Se instalan mediante:

```powershell
python -m pip install -r requirements-google-drive.txt
```

## Alcance OAuth

Atlas solicita exclusivamente:

```text
https://www.googleapis.com/auth/drive.readonly
```

No se solicitan permisos de creación, edición, eliminación ni compartición.

## Archivos privados

```text
data/integrations/google_drive/credentials.json
data/integrations/google_drive/token.json
```

Ambos quedan excluidos de Git.

## Funcionamiento del arranque

1. Atlas registra inicialmente la herramienta de Drive desactivada.
2. Intenta cargar un token existente de forma no interactiva.
3. Nunca abre el navegador durante el arranque.
4. Si el token es válido, activa automáticamente Google Drive.
5. Si falta cualquier elemento, Atlas continúa normalmente.

## Autorización inicial

```powershell
python scripts/configure_google_drive.py
```

La primera ejecución abre el navegador para que el propietario autorice el
acceso de solo lectura. Las ejecuciones posteriores reutilizan y, cuando es
posible, renuevan el token local.

## Restricción por carpeta

`GoogleDriveOAuthConfig` acepta `root_folder_id`. Cuando se configura, el
cliente valida que las carpetas y documentos estén dentro de esa raíz antes de
leerlos.

## Formatos textuales

- Google Docs se exporta como texto plano.
- Google Sheets se exporta como CSV.
- Google Slides se exporta como texto plano.
- Los archivos de texto subidos se descargan directamente.
- Los binarios, como PDF, se rechazan en esta etapa.

## Seguridad

- importación diferida de las librerías de Google;
- acceso de solo lectura;
- autorización interactiva explícita;
- token local fuera de Git;
- ausencia de navegador durante el arranque;
- restricción opcional a una carpeta;
- rechazo de formatos binarios;
- Atlas sigue operativo ante cualquier error de integración.
