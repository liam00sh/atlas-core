# Guía de uso

## Primer inicio

1. Inicie `python -m atlas_dataset_studio`.
2. Pulse **Dataset > Abrir**.
3. Seleccione `metadata_daxter.csv` y la carpeta `02_limpios`.
4. Para una primera comprobación, use una copia de los metadatos. Los WAV pueden mantenerse en su ubicación original porque el reproductor nunca los modifica.

La aplicación recuerda el último proyecto. Si detecta un lock activo ofrece abrirlo en modo solo lectura.

## Revisión

La columna izquierda busca por identificador, archivo y texto, y combina filtros de juego, estado, expresión, personalidad y pendientes. Se puede saltar a una posición o `sample_id` exacto.

En **Revisión**:

- reproduzca, pause, detenga o reinicie el WAV;
- compare texto verificado y texto normalizado;
- elija una de las 15 expresiones y su confianza;
- clasifique intención, energía, intensidad, calidad y estado;
- marque etiquetas múltiples de personalidad y utilidad conversacional;
- use **Propuesta automática** para inspeccionar la heurística y **Aplicar propuesta** para copiarla al formulario;
- guarde o use **Aceptar y siguiente**.

Los cambios relevantes activan autosave tras una pausa breve. `accepted_with_notes` se usa cuando una muestra válida necesita observaciones. No se deben aceptar muestras en bloque sin escucharlas.

## Pestañas

- **Estadísticas**: totales, duración, progreso y distribuciones.
- **Personalidad**: acceso rápido a frases icónicas; los filtros permiten explorar humor, burla, competición, menciones a Jak y combinaciones.
- **Validación**: comprueba estructura, WAV PCM, hashes, categorías, duplicados y ausencias.
- **Configuración**: preset, rutas efectivas, workspace, backups y modo de apertura.

## Atajos

- `Space`: reproducir o pausar.
- `Ctrl+Right` / `Ctrl+Left`: siguiente / anterior.
- `Ctrl+S`: guardar.
- `Enter`: aceptar y avanzar.
- `Alt+1` a `Alt+0`, después `F6` a `F10`: las 15 expresiones en el orden del preset `daxter_es`.

## Exportación

**Dataset > Exportar** genera `metadata.csv`, `metadata.jsonl`, `manifest.json`, `tts_dataset.jsonl`, `personality_dataset.jsonl`, `review_queue.csv` y `DATASET_VALIDATION_REPORT.md`. El dataset no se declara cerrado mientras existan errores o muestras pendientes.

