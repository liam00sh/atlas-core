# Revisión Telegram multimedia, STT y visión

Fecha: 2026-08-06

Rama: `feature/telegram-multimedia-stt-vision`

Base exacta: `daebe6bd` (`origin/main`)
Worktree seguro: `C:\Proyectos\Atlas\atlas_core_multimedia`

## 1. Inventario inicial

Antes de editar se verificó `origin/main`, el merge `daebe6bd`, el estado de los worktrees y la suite completa. El checkout original `atlas_core` contenía cambios locales y datos personales/operativos mezclados; no se modificó. Se creó un worktree hermano limpio desde `origin/main` para no perder ni cruzar trabajo previo.

Estado inicial de la base limpia:

- `953 passed, 2324 subtests passed in 158.25s`.
- Comprobación Telegram offline correcta: almacenamiento e integración disponibles; Telegram y token desactivados; conexión real omitida.
- Implementado: identidad vinculada, sesiones, permisos, auditoría minimizada, métricas por etapa, long polling, descarga parcial, TTS local y transporte de texto.
- Parcial: descarga multimedia monolítica, basada en MIME declarado; `analyze_media` opcional sin proveedor; métodos de envío multimedia ausentes.
- No conectado: STT, visión, documentos, reconocimiento facial privado y respuesta de voz Telegram en `main`.
- Inseguro/incompleto: no había comprobación común de firma real, protección DOCX/ZIP, límites por tipo, saneado EXIF, raíz de salida controlada ni contrato facial consentido.
- Obsoleto/no aplicable: vídeo y animaciones se aceptaban en el transporte anterior sin una validación suficientemente específica; ahora quedan fuera.
- Duplicado: no se creó un núcleo conversacional alternativo. La capa multimedia termina en `AtlasCoreAdapter.process()`, que invoca el `Atlas.process()` normal con identidad y sesión vinculadas.

La documentación consultada en Drive confirmaba que la multimedia avanzada, STT y biometría estaban pendientes y que debían reutilizar el mismo núcleo y no ampliar permisos por el canal.

## 2. Arquitectura resultante

```text
Update Telegram
  -> TelegramMediaEnvelope
  -> TelegramMediaDownloader
  -> TelegramMediaQuarantine
  -> TelegramMediaValidator (firma/MIME/estructura real)
  -> procesador especializado inyectado
       voice/audio -> FFmpeg -> WAV mono 16 kHz -> BaseSTTProvider
       photo       -> normalizador sin EXIF -> ImageAnalyzerProtocol
       document    -> DocumentAnalyzerProtocol
       rostro      -> FaceRecognitionProvider + galería privada autorizada
  -> resultado estructurado o transcripción
  -> AtlasCoreAdapter.process(usuario, canal, sesión)
  -> texto o TelegramVoiceRenderer según preferencia del usuario
  -> envío Telegram
  -> limpieza en finally
```

Módulos principales:

- `telegram_interface/media.py`: sobre, límites, descarga, firma real, cuarentena y limpieza.
- `voice/stt.py`: `BaseSTTProvider`, adaptador local `FasterWhisperSTTProvider`, conversión y servicio con timeout.
- `telegram_interface/multimedia.py`: único orquestador hacia el núcleo.
- `telegram_interface/analyzers.py`: contratos de imagen/documento y extractores locales seguros.
- `identity/face_recognition.py`: galería y política facial privada.
- `telegram_interface/voice_delivery.py`: WAV a OGG/Opus sin reproducción local.
- `telegram_interface/outbound.py` y `tools/telegram_media.py`: envío desde raíces permitidas.

## 3. Transporte y cuarentena

El flujo común admite inicialmente `voice`, `audio`, `photo` y `document`. Vídeo y animaciones se rechazan en la frontera.

Controles aplicados:

- límites independientes y configurables por tipo;
- `getFile` y descarga con timeout del cliente;
- nombres locales aleatorios, no derivados del usuario;
- cuarentena con permisos restrictivos cuando el sistema los admite;
- firma y MIME reales, sin confiar en extensión, nombre o MIME de Telegram;
- rechazo de ejecutables, scripts, políglotas, rutas remotas inseguras y descargas que escapen de cuarentena;
- JPEG/PNG/RIFF/PDF/DOCX con comprobaciones estructurales;
- rechazo de contenido PDF activo, macros, ejecutables, path traversal y zip bombs en DOCX;
- MP4 genérico no se acepta como audio demostrado; solo marcas M4A/M4B;
- hash completo solo en memoria del sobre; no se escribe en auditoría;
- borrado de cuarentena en `finally` y limpieza por TTL.

## 4. STT y voz

El proveedor implementado es un adaptador desacoplado para `faster-whisper`. No se instaló la librería ni se descargó modelo alguno. Por defecto no permite descargas y solo se considera disponible si existe el paquete y un modelo local configurado, salvo autorización explícita futura.

Flujo de voz:

- duración declarada excesiva: rechazo antes de descargar;
- conversión limitada a WAV PCM mono, 16 kHz;
- audio vacío, corrupto, excesivo, timeout o motor ausente: respuesta clara y sin llamada al núcleo;
- idioma automático por defecto y pista opcional por usuario (`es`, `ca`, `en` comprobados con dobles);
- transcripción normalizada y entregada una sola vez al núcleo;
- transcripción nunca incluida en auditoría técnica;
- WAV temporal retirado tras éxito/error y con limpieza diferida si un proveedor excede el timeout.

La salida hablada:

- conserva `automatic`, `text_only` y `audio_only` por usuario y de forma persistente;
- automático devuelve voz a una entrada de voz y texto a una entrada escrita;
- usa personalidad, voz, velocidad y volumen del usuario vinculado;
- `VoiceService.speak(..., play_audio=False)` evita reproducción en el PC;
- genera WAV, lo convierte a OGG/Opus para `sendVoice` y elimina ambos;
- cae a un único texto si falla TTS, FFmpeg, renderizado o Telegram;
- no vuelve a ejecutar la acción del núcleo al fallar el envío.

## 5. Imágenes y documentos

`ImageAnalyzerProtocol` separa Telegram del proveedor de visión. Antes de analizar se exige un normalizador que corrija orientación, limite píxeles y vuelva a codificar sin EXIF. Sin normalizador o proveedor local, la función responde que no está disponible y no envía la imagen a servicios externos.

Operaciones representadas por el contrato: descripción, pregunta visual, OCR, objetos generales, capturas y comparación. La comparación de varias imágenes existe en el protocolo del proveedor, pero el agrupado temporal de un álbum Telegram (`media_group_id`) no se activa todavía; requiere una decisión de UX/timeout y pruebas con transporte real simulado antes de habilitarlo.

Los resultados visuales se limitan antes de llegar al núcleo y se marcan como datos no confiables. No se permite inferencia de identidad ni de atributos sensibles en el análisis general.

Documentos admitidos:

- TXT, Markdown y JSON locales;
- PDF local con `pypdf`, límite de páginas, cifrado rechazado y extracción acotada;
- imágenes mediante el flujo visual;
- DOCX solo cuando exista `python-docx`; el transporte ya rechaza macros, ejecutables y ZIP peligrosos.

No hay persistencia automática. El contenido se copia dentro de cuarentena, se limita, se entrega una vez al núcleo y se elimina.

## 6. Política facial privada

El reconocimiento facial queda desactivado si no se inyecta un proveedor local. Solo se activa ante una orden facial explícita exacta y con `face.recognize`.

Reglas implementadas:

- solo chat privado, cuenta vinculada y usuario no invitado;
- alta/revocación reservadas a administrador con permiso específico y confirmación reforzada;
- varias fotos y exactamente un rostro claro por muestra durante el alta;
- comparación únicamente con la galería local consentida y con la misma versión de modelo;
- umbral alto: identidad interna autorizada; umbral intermedio: posible coincidencia sin revelar identidad; resto: persona no reconocida;
- sin Internet, personas públicas, vigilancia, grupos, cámaras, seguimiento ni historial de apariciones;
- sin inferir raza, salud, religión, orientación, género, emoción u otros atributos sensibles;
- galería: identificador interno, embeddings, versión, consentimiento, fechas y estado activo/revocado;
- no almacena fotos, nombres completos, ubicaciones ni apariciones;
- galería corrupta nunca se sobrescribe silenciosamente;
- revocación, desactivación y regeneración disponibles en el servicio.

Permisos: `face.enroll`, `face.recognize`, `face.revoke`, `face.status`. El resolvedor predeterminado de Atlas no los concede automáticamente. El canal solo los deja pasar si un resolvedor central los concedió explícitamente.

La conversación completa de alta con acumulación de varias fotos no se habilita mientras no exista un proveedor local elegido y una prueba manual autorizada. El almacén y el servicio de política están listos y probados con dobles.

## 7. Envío de archivos desde Atlas

Herramientas separadas:

- `telegram.send_photo`
- `telegram.send_voice`
- `telegram.send_audio`
- `telegram.send_document`

La herramienta no acepta un destino libre: resuelve siempre el chat vinculado del usuario autenticado. Solo acepta `root` autorizada y `relative_path`; ignora cualquier `chat_id` aportado. Rechaza rutas absolutas, `..`, raíces desconocidas, enlaces fuera de raíz, MIME falso, ejecutables y tamaños excesivos. Datos personales requieren `confirmed=true`. Solo la raíz `generated` admite borrado posterior explícito.

Raíces del runtime:

- `data/integrations/telegram/outbox/`
- `data/integrations/telegram/outbox/generated/`

Ambas quedan fuera de Git.

## 8. Métricas y rendimiento

Etapas técnicas añadidas y aceptadas por la auditoría:

- `media.download`, `media.validation`, `audio.convert`, `stt.transcribe`;
- `image.analyze`, `face.detect`, `face.compare`, `document.extract`;
- `tts.synthesize`, `telegram.upload`.

Solo se registran nombre de etapa, duración, tipo, tamaño y resultado. No se registran mensaje, transcripción, nombre, localidad, ruta, imagen, audio, embedding ni hash completo.

No se puede dar un antes/después real de latencia Telegram: por regla de seguridad no se conectó el bot ni se activaron TTS/STT/visión reales. Las pruebas verifican una sola descarga, una transcripción, una llamada al núcleo, una síntesis cuando corresponde y un envío final. El mensaje de espera existente conserva el umbral configurable y no duplica el trabajo.

## 9. Configuración y dependencias

Variables nuevas/reutilizadas:

- `ATLAS_TELEGRAM_VOICE_MAX_BYTES`
- `ATLAS_TELEGRAM_AUDIO_MAX_BYTES`
- `ATLAS_TELEGRAM_PHOTO_MAX_BYTES`
- `ATLAS_TELEGRAM_DOCUMENT_MAX_BYTES`
- `ATLAS_TELEGRAM_MEDIA_TTL_HOURS`
- `ATLAS_STT_MAX_AUDIO_SECONDS`
- `ATLAS_STT_MODEL`
- `ATLAS_STT_MODEL_PATH`
- `ATLAS_STT_DEVICE` (`cpu`/GPU según soporte del motor)
- `ATLAS_STT_COMPUTE_TYPE`
- `ATLAS_STT_TIMEOUT_SECONDS`
- `ATLAS_STT_ALLOW_MODEL_DOWNLOAD` (predeterminado: `false`)

Estado local detectado:

- FFmpeg: disponible.
- `pypdf`: disponible.
- Pillow: no instalado.
- `python-docx`: no instalado.
- `faster-whisper`: no instalado.
- proveedor facial: no instalado/configurado.
- proveedor de visión: no configurado.

No se añadió ni instaló ninguna dependencia y no se descargaron modelos.

## 10. Archivos y datos excluidos

`.gitignore` cubre ahora además:

- `data/telegram_media/`
- `data/voice/stt/`
- `data/face/`
- `data/biometrics/`
- `data/integrations/telegram/outbox/`

Comprobaciones finales:

- ningún patrón de secreto en producción ni en archivos cambiados;
- ninguna ruta absoluta nueva en archivos cambiados;
- ningún runtime, cuarentena, outbox, embedding, audio, documento o imagen nuevo rastreado;
- dos PNG de evidencias de tests ya existían en `origin/main`; esta rama no añade multimedia al repositorio;
- el checkout original y sus datos locales no fueron borrados, movidos ni sobrescritos.

## 11. Archivos modificados

Código principal añadido/modificado:

- `.gitignore`
- `core/request_timing.py`
- `identity/face_recognition.py`
- `telegram_interface/{analyzers,audit,client,config,gateway,media,models,multimedia,outbound,polling,response_modes,runtime,storage,voice_delivery}.py`
- `tools/atlas_adapter.py`
- `tools/telegram_media.py`
- `voice/preferences/manager.py`
- `voice/service.py`
- `voice/stt.py`

Pruebas añadidas/ampliadas:

- `tests/identity/test_private_face_recognition.py`
- `tests/telegram/test_image_document_analysis.py`
- `tests/telegram/test_media_transport_secure.py`
- `tests/telegram/test_outbound_media_tools.py`
- `tests/telegram/test_stt_service.py`
- `tests/telegram/test_voice_delivery_multimedia.py`
- `tests/test_voice_service.py`

## 12. Pruebas y resultados

Validación final exacta:

- Suite completa: `1011 passed, 1 skipped, 2324 subtests passed in 153.46s`.
- Omisión: prueba de symlink fuera de raíz; Windows no concedió privilegio para crear el enlace. La comprobación de producción usa `resolve()` + `relative_to()` y la prueba se ejecuta donde el sistema permita symlinks.
- Telegram + facial durante cierre: `153 passed, 1 skipped`.
- Endurecimiento focal final: `44 passed, 1 skipped`.
- `python -m compileall -q .`: correcto.
- `git diff --check`: correcto.
- `python scripts/check_telegram_config.py --offline`: correcto; conexión real omitida.
- Revisión de secretos, rutas absolutas y archivos generados rastreados: correcta para los cambios.

## 13. Commits locales

1. `1b16477 feat(telegram): añade transporte multimedia seguro`
2. `e04adcf feat(stt): integra transcripción local de notas de voz`
3. `1bc592f fix(voice): completa respuestas habladas y fallbacks`
4. `eaef35f feat(face): añade reconocimiento privado con consentimiento`
5. `6141221 feat(vision): añade análisis modular de imágenes y documentos`
6. `0c10036 feat(telegram): envía archivos desde rutas autorizadas`
7. `c44bc36 fix(multimedia): limita duración y tiempo de análisis`
8. `28cdd91 fix(security): endurece límites y cuarentena multimedia`

No se hizo push, merge ni reescritura de historial.

## 14. Riesgos y pruebas manuales pendientes

- Elegir e instalar un único motor STT local y un modelo local autorizado.
- Elegir/configurar un proveedor visual local y Pillow antes de activar imágenes.
- Instalar `python-docx` solo si se decide habilitar DOCX.
- Elegir un proveedor facial local antes de habilitar alta/consulta; registrar rostros reales requiere autorización expresa y consentimiento.
- Definir UX y timeout para agrupar álbumes Telegram y comparar varias imágenes en una solicitud.
- Probar manualmente, con autorización, un bot de pruebas: descarga, STT, respuesta OGG/Opus, fallbacks y tiempos reales.
- Verificar GPU/CPU, latencia de modelos y límites definitivos en el equipo de destino.
- Valorar cifrado del almacén biométrico en reposo mediante una clave externa al repositorio.

## 15. Recomendación y comandos para REDACTED_2c7b6821719d

Recomendación: revisar esta rama completa y abrir un pull request. Los commits son dependientes y forman una sola arquitectura; no se recomienda cherry-pick parcial salvo revisión técnica específica.

Siguiente comprobación, sin publicar:

```powershell
Set-Location C:\Proyectos\Atlas\atlas_core_multimedia
git status -sb
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
python -m pytest -q
python scripts/check_telegram_config.py --offline
```

Después de revisar y autorizar expresamente la publicación:

```powershell
git push -u origin feature/telegram-multimedia-stt-vision
```

Después, crear un pull request hacia `main`; no hacer merge directo desde el equipo local.
