# Activación final de STT de Atlas

Fecha de revisión: 2026-08-06  
Rama: `feature/stt-confidence-production`  
Base: `origin/main` en `884d340` (merge de la integración multimedia)  
Worktree: revisión aislada; el checkout original con cambios locales no se modificó.

## 1. Inventario inicial

- Suite inicial: `1011 passed, 1 skipped, 2324 subtests passed in 157.48s`.
- Telegram offline: almacenamiento e integración disponibles; bot y token no configurados en este worktree limpio; no se hizo conexión real.
- FFmpeg: instalado y accesible, versión 8.1.2.
- `faster-whisper`: 1.2.1.
- `ctranslate2`: 4.8.1.
- GPU detectada: NVIDIA GeForce RTX 4060, controlador 591.86, 8188 MiB.
- CTranslate2 enumera una GPU CUDA, pero `cublas64_12.dll` y `cudnn64_9.dll` no están accesibles.
- La caché del modelo `small` solo contiene la referencia de revisión; no contiene un snapshot completo cargable.
- Ninguna variable `ATLAS_STT_*` estaba definida.

El código previo ya tenía conversión segura con FFmpeg, límite de duración, timeout, limpieza, proveedor desacoplado y entrada única en `Atlas.process()`. Faltaban selección automática GPU/CPU, detección real del modelo local, métricas de confianza, bloqueo preventivo de transcripciones inciertas, diagnóstico operativo y guía CUDA.

La revisión posterior detectó una discrepancia real: el flujo de validación requería `--live RUTA_AUDIO`, pero el script solo exponía `--load-model`. Además, `--load-model` podía heredar una autorización de descarga del entorno. Ambos problemas están corregidos: existen los tres modos y la herramienta fuerza descargas desactivadas en todos ellos.

## 2. Causa raíz

Había tres causas relacionadas:

1. `FasterWhisperSTTProvider.is_available()` solo aceptaba una ruta de modelo explícita o descargas habilitadas. No resolvía un modelo completo desde la caché local y, en este equipo, la caché encontrada está incompleta.
2. La configuración fijaba CPU/int8 y no comprobaba si CUDA podía cargarse realmente. CTranslate2 detecta la GPU, pero faltan las bibliotecas de ejecución de CUDA 12 y cuDNN 9.
3. La transcripción descartaba `avg_logprob`, `no_speech_prob` y `language_probability` y enviaba cualquier texto no vacío directamente a Atlas. Una hipótesis dudosa podía llegar a comandos, herramientas o memoria.

Además, el nombre documentado `ATLAS_STT_TIMEOUT` no coincidía con el único nombre aceptado (`ATLAS_STT_TIMEOUT_SECONDS`).

## 3. Arquitectura final

El flujo queda así:

`Telegram voice/audio -> cuarentena -> FFmpeg WAV mono 16 kHz -> faster-whisper local -> Speech Confidence -> Intent Confidence -> decisión/confirmación/aclaración -> Atlas.process() como máximo una vez -> respuesta -> limpieza`

- `STTConfig`: configuración desde entorno, con compatibilidad para el alias antiguo del timeout.
- `resolve_stt_backend()`: intenta CUDA y usa CPU/int8 si la GPU o sus DLL no están operativas.
- `find_local_faster_whisper_model()`: solo declara listo un snapshot con los archivos mínimos reales.
- `FasterWhisperSTTProvider`: carga perezosa, sin descarga predeterminada, extrae evidencia del modelo y reintenta una sola vez en CPU si CUDA falla al cargar o inferir.
- `STTInputPolicy`: frontera determinista compartida por Telegram y una entrada CLI; no contiene una IA paralela.
- `TelegramMultimediaProcessor`: solo llama a `Atlas.process()` cuando la decisión es `PROCESS`.

## 4. Configuración

Variables documentadas en `.env.example`:

- `ATLAS_STT_MODEL=small`
- `ATLAS_STT_DEVICE=auto` (`auto`, `cuda`/`gpu` o `cpu`)
- `ATLAS_STT_COMPUTE_TYPE=auto` (`float16` en CUDA e `int8` en CPU por defecto)
- `ATLAS_STT_TIMEOUT=90`
- `ATLAS_STT_MAX_AUDIO_SECONDS=180`
- `ATLAS_STT_LANGUAGE_HINT=` (vacío conserva detección automática)
- `ATLAS_STT_ALLOW_MODEL_DOWNLOAD=false`

Se mantiene compatibilidad con `ATLAS_STT_TIMEOUT_SECONDS`. El idioma detectado, la pista STT y la voz TTS permanecen separados. No existe hoy una preferencia STT persistente por usuario; Telegram conserva el resolver inyectable y, mientras no haya una preferencia explícita, usa detección automática en vez de inferirla de la voz TTS.

## 5. GPU y fallback CPU

Prioridad con `ATLAS_STT_DEVICE=auto`:

1. CUDA si CTranslate2 detecta dispositivo y las bibliotecas requeridas son accesibles.
2. CPU/int8 si falta CUDA, cuDNN, una DLL o la inicialización/inferencia CUDA falla.

El motivo técnico del fallback se expone en `health()` y en el diagnóstico, sin contenido de audio ni rutas privadas. El log solo guarda el tipo de error; no guarda transcripción, audio ni nombre de archivo.

Estado de este equipo: fallback preventivo a CPU porque faltan `cublas64_12.dll` y `cudnn64_9.dll`. No se instaló software ni se copiaron DLL.

## 6. Dos niveles independientes de confianza

### Speech Confidence

Responde únicamente a: «¿se han entendido correctamente las palabras?». No intenta decidir qué acción quiere el usuario.

Evidencia utilizada:

- media ponderada por duración de `avg_logprob`;
- máximo de `no_speech_prob` de los segmentos;
- `language_probability` del resultado.
- probabilidades media y mínima por palabra;
- máximo de `compression_ratio`;
- duración de voz después de VAD;
- RMS, pico, proporción de silencio y proporción de clipping del WAV normalizado.

Umbrales conservadores actuales:

| Nivel | Evidencia base | Evidencia adicional | Acción acústica |
|---|---|---|---|
| Alta | `avg_logprob >= -0.55`, `no_speech <= 0.35`, idioma `>= 0.50` | palabra `>= 0.70`, compresión `<= 2.4`, VAD y audio aptos | continúa a intención |
| Media | `avg_logprob >= -1.05`, `no_speech <= 0.65`, idioma `>= 0.25` | palabra `>= 0.45`, compresión `<= 3.0`, calidad mínima | pide confirmación |
| Baja | no cumple media | ruido, silencio, clipping o VAD insuficiente | nunca ejecuta |

### Intent Confidence

Responde a: «¿Atlas sabe realmente qué quiere hacer el usuario?». Se calcula después de la transcripción y de forma separada. `AtlasIntentConfidenceResolver` coordina, sin ejecutar, los resolvers existentes de hogar, Windows, comandos registrados y preflight ejecutivo. También considera entidades, argumentos obligatorios, slots pendientes, historial inmediato y la presencia de memoria temporal de la sesión.

- **Alta:** intención y argumentos suficientes; puede continuar si Speech también es alta.
- **Media:** intención probable pero falta confirmar un dato, por ejemplo un recordatorio sin hora.
- **Baja:** orden incompleta o referencia ambigua; solicita una aclaración concreta.

Matriz final:

| Speech | Intent | Decisión |
|---|---|---|
| Alta | Alta | `PROCESS` |
| Alta | Media/Baja | `ASK_FOR_CLARIFICATION` |
| Media | cualquiera | `WAIT_FOR_CONFIRMATION` |
| Baja | cualquiera | `ASK_TO_REPEAT` |

Una orden sensible exige Speech alta aunque Intent sea alta. Un «sí» posterior no eleva una orden sensible transcrita con confianza media: debe repetirse completa.

Las aclaraciones se mantienen como estado efímero en RAM, aislado por `session_id` y con caducidad de 120 segundos. No se escriben en memoria, auditoría ni disco. Solo la frase confirmada/completada llega una vez a Atlas y podrá seguir las reglas normales de memoria.

## 7. Seguridad, privacidad y Telegram

- No se persiste audio ni transcripción desde esta política; una hipótesis pendiente vive solo en RAM y caduca.
- Las respuestas de duda son efímeras y vuelven al mismo chat privado vinculado.
- No se añadió contenido a auditorías; solo se conservan métricas por etapa ya existentes.
- El audio temporal convertido se elimina en éxito, error y timeout.
- La cuarentena multimedia sigue limpiándose al terminar el trabajo del poller.
- El progreso existente espera el umbral configurable, se envía una sola vez y no se usa para comandos rápidos.
- No hubo bot real, red Telegram, transcripción real, modelo remoto ni descarga. El audio local autorizado solo se leyó para validar formato y alcanzar el proveedor inactivo.

## 8. Diagnóstico y asistente CUDA

`python scripts/check_stt_config.py` tiene tres modos coherentes con la implementación:

- sin argumentos: diagnóstico offline;
- `--load-model`: carga solo un modelo ya local;
- `--live RUTA_AUDIO`: valida la firma, convierte con `AudioConverter`, transcribe con `STTService` y muestra proveedor, backend, modelo, idioma, duración, texto, métricas, Speech Confidence, Intent Confidence y decisión.

Los tres modos fuerzan `allow_model_download=False`, incluso si el entorno heredado contiene `ATLAS_STT_ALLOW_MODEL_DOWNLOAD=true`. `--live` no llama a `Atlas.process()`, Telegram, memoria ni auditoría y elimina el WAV en todos los caminos.

`python scripts/guide_stt_cuda_install.py` es de solo lectura. Identifica las DLL exactas, enlaza las descargas oficiales y muestra cómo verificar. No instala, no cambia PATH y desaconseja copiar DLL sueltas.

Resultado actual del diagnóstico: OK para Python, FFmpeg, faster-whisper, CTranslate2, GPU y disco; WARNING para las dos DLL, fallback CPU, variables no definidas, modelo incompleto y proveedor inactivo.

## 9. Archivos modificados o añadidos

- `.env.example`: configuración STT y umbral de progreso.
- `.gitignore`: exclusión del directorio local de pytest usado en esta revisión.
- `requirements-stt.txt`: dependencia Python opcional, sin instalación automática.
- `voice/stt.py`: configuración, backend, caché, métricas, confianza y fallback.
- `voice/stt_policy.py`: política común de ejecución/confirmación/repetición/aclaración.
- `voice/stt_diagnostics.py`: diagnóstico reutilizable.
- `telegram_interface/multimedia.py`: aplicación de la política antes de Atlas.
- `telegram_interface/core_adapter.py`: lectura aislada del contexto temporal por sesión.
- `telegram_interface/gateway.py`: resolución de confirmaciones/aclaraciones STT escritas.
- `scripts/check_stt_config.py`: diagnóstico, carga local y prueba `--live`.
- `scripts/guide_stt_cuda_install.py`: guía CUDA/cuDNN.
- `tests/telegram/test_stt_confidence_production.py`: regresiones offline.
- `tests/telegram/test_stt_live_and_intent_confidence.py`: dos confianzas, `--live`, seguridad y estado efímero.
- `CODEX_ACTIVACION_STT_FINAL.md`: este informe.

## 10. Pruebas añadidas

- configuración nueva y alias anterior de timeout;
- caché completa e incompleta;
- fallback por DLL CUDA ausente;
- fallo CUDA durante inferencia y reintento único en CPU;
- confianza alta, media y baja;
- intención alta, media y baja independiente de la confianza acústica;
- métricas de palabras, VAD, compresión, ruido, silencio y clipping;
- español, valenciano/catalán e inglés;
- ruido/confianza baja;
- orden sensible sin ejecución ni memoria;
- comandos incompletos;
- equivalencia de política para CLI;
- validación de firma, transcripción local simulada y limpieza de `--live`;
- confirmación, corrección, caducidad y aislamiento de aclaraciones por sesión;
- Telegram sin llamada al núcleo en duda;
- Telegram con una sola llamada al núcleo en confianza alta.

Los tests preexistentes ya cubren audio vacío/corrupto, duración, timeout, FFmpeg ausente, limpieza, aislamiento de usuario/sesión, deduplicación y transporte seguro.

## 11. Resultados exactos

- Baseline: `1011 passed, 1 skipped, 2324 subtests passed in 157.48s`.
- STT focal final: `58 passed in 0.82s`.
- Telegram relacionado con entrega/progreso: `26 passed in 0.42s`.
- Telegram completo final: `196 passed, 1 skipped in 4.75s`.
- Voz: `9 passed in 0.11s`.
- Suite final sobre el diff definitivo: `1056 passed, 1 skipped, 2324 subtests passed in 156.07s`.
- `compileall`: correcto.
- `git diff --check`: correcto.
- búsqueda de patrones de secretos en archivos rastreados: sin coincidencias.
- rutas absolutas locales añadidas: ninguna.
- Telegram offline: correcto; conexión real omitida.
- `check_stt_config.py --help`: muestra `--load-model | --live RUTA_AUDIO`.
- `check_stt_config.py`: diagnóstico offline correcto.
- `check_stt_config.py --load-model`: no descargó; caché antes/después `1/1` archivos incluso heredando permiso `true`.
- `check_stt_config.py --live C:\Proyectos\Atlas\pruebas\voz_Alex.oga`: formato aceptado y salida controlada `stt_unavailable` por ausencia del modelo; ningún temporal restante.

## 12. Rendimiento

El archivo autorizado `C:\Proyectos\Atlas\pruebas\voz_Alex.oga` superó la validación de formato y el comando `--live` llegó de forma segura hasta el proveedor. La transcripción real se detuvo con `stt_unavailable` porque no existe un snapshot completo del modelo. No se inventan tiempos. El flujo mantiene una conversión, una transcripción y como máximo una llamada a Atlas.

## 13. Riesgos y pruebas manuales pendientes

- Descargar o proporcionar el modelo `small` completo.
- Elegir CPU inmediata o instalar CUDA Toolkit 12 y cuDNN 9 oficiales para GPU.
- Medir carga en frío, transcripción CPU y transcripción GPU con audios ficticios autorizados.
- Calibrar umbrales con un corpus privado de prueba sin conservar audios/transcripciones.
- Probar un bot real solo con autorización expresa.
- La confianza es una política conservadora basada en evidencia del decodificador, no una probabilidad absoluta de que cada palabra sea correcta.

## 14. Estado Git y publicación

No se creó commit, no se hizo merge y no se hizo push. El repositorio original `atlas_core` y sus cambios locales permanecen intactos. La entrega está en la rama aislada `feature/stt-confidence-production`, basada en `origin/main`.

## 15. Pasos exactos para Alex

### Opción recomendada: activar primero en CPU

Después de que Alex proporcione o descargue el modelo por un procedimiento separado y expresamente autorizado:

```powershell
cd C:\Proyectos\Atlas\atlas_core
python -m pip install -r requirements-stt.txt
$env:ATLAS_STT_DEVICE='cpu'
$env:ATLAS_STT_COMPUTE_TYPE='int8'
$env:ATLAS_STT_MODEL='small'
$env:ATLAS_STT_ALLOW_MODEL_DOWNLOAD='false'
python scripts/check_stt_config.py --load-model
python scripts/check_stt_config.py --live 'C:\Proyectos\Atlas\pruebas\voz_Alex.oga'
```

`check_stt_config.py` nunca descarga, aunque la variable esté accidentalmente en `true`. Después, guardar en el `.env` privado `ATLAS_STT_ALLOW_MODEL_DOWNLOAD=false` y la configuración elegida. No subir `.env`.

### Opción GPU

```powershell
cd C:\Proyectos\Atlas\atlas_core
python scripts/guide_stt_cuda_install.py
where.exe cublas64_12.dll
where.exe cudnn64_9.dll
$env:ATLAS_STT_DEVICE='auto'
$env:ATLAS_STT_COMPUTE_TYPE='auto'
$env:ATLAS_STT_ALLOW_MODEL_DOWNLOAD='false'
python scripts/check_stt_config.py --load-model
```

Instalar previamente CUDA Toolkit 12 y cuDNN 9 desde NVIDIA, reiniciar la terminal y no copiar DLL individuales.

### Tras la prueba manual autorizada

```powershell
python -m pytest -q
git diff --check
git status -sb
```

Solo después de revisar que no hay datos ni modelos en el diff, Alex podrá decidir commits y publicación. No se recomienda arrancar Telegram real hasta que `check_stt_config.py --load-model` indique proveedor activo.
