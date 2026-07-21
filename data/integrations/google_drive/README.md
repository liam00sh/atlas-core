# Google Drive — archivos locales

Esta carpeta contiene la configuración local de Google Drive para Atlas.

Archivos esperados:

```text
credentials.json
token.json
```

- `credentials.json` se descarga desde Google Cloud al crear un cliente OAuth
  de tipo **Aplicación de escritorio**.
- `token.json` lo crea automáticamente el script de autorización.
- Ambos archivos están excluidos mediante `.gitignore`.
- No deben enviarse, compartirse ni copiarse a la documentación.

La autorización se inicia con:

```powershell
python scripts/configure_google_drive.py
```

Atlas solicita únicamente acceso de lectura a Google Drive.
