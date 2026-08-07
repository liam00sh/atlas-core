# Atlas Dataset Studio

Atlas Dataset Studio v1 es una aplicación local para revisar, etiquetar, validar y exportar datasets de voz y personalidad. Vive en el repositorio como herramienta de desarrollo independiente: no importa `Atlas`, no arranca servicios y no contacta Internet, Ollama, Telegram, Home Assistant, Google Drive ni Raspberry durante su uso.

## Arquitectura

- `atlas_dataset_studio/app`: interfaz PySide6, navegación, audio, pestañas y atajos.
- `dataset.py`: sesión de revisión, búsquedas, filtros, progreso y autosave.
- `models.py`: esquema conservador y migración del formato v1.
- `storage.py`: lectura, escritura atómica, snapshots, recuperación y lock.
- `suggestions.py`: contrato `DatasetSuggestionProvider` y heurística local.
- `validators.py`: WAV PCM, esquema, duplicados y SHA-256.
- `exporters.py`: datasets derivados, manifiesto e informe de cierre.
- `config.py`: configuraciones y última sesión en `%LOCALAPPDATA%`.

Los WAV se cargan bajo demanda mediante Qt Multimedia. Solo se versionan código, preset y documentación; las rutas del usuario, locks, estados, backups y exportaciones permanecen locales.

## Instalación y arranque

```powershell
cd C:\Proyectos\Atlas\atlas_core
python -m pip install -r requirements.txt
python -m pip install -r requirements-dataset-studio.txt
python -m atlas_dataset_studio
```

En Windows también puede ejecutarse `run_dataset_studio.cmd`.

Al abrir un dataset se eligen los metadatos (`.csv` o `.jsonl`) y la carpeta WAV. La aplicación crea su workspace privado bajo `%LOCALAPPDATA%\AtlasDatasetStudio`; nunca guarda esas rutas en Git.

## Garantías de v1

- `text` es de solo lectura y nunca se reemplaza desde la edición normal.
- `normalized_text` conserva su valor original y puede restaurarse.
- toda decisión de emoción aplicada desde la interfaz queda con origen humano;
- las propuestas heurísticas no marcan muestras como revisadas ni se aplican solas;
- cada guardado toma snapshot, escribe un temporal sincronizado y hace reemplazo atómico;
- un cambio externo bloquea el guardado;
- una segunda instancia solo puede abrir con seguridad en modo lectura;
- ninguna exportación contiene rutas absolutas.

