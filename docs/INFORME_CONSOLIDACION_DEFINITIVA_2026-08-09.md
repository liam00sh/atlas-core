# Consolidación definitiva de Atlas Core — 9 de agosto de 2026

## Resultado

La única copia operativa de Atlas queda establecida en
`C:\Proyectos\Atlas\atlas_core`. Los servicios programados de escritorio,
monitorización y Telegram usan esa ruta. Los laboratorios
`atlas_fase6_daxter_tts_lab` y `atlas_dataset_studio_worktree` continúan
separados porque son entornos de investigación, no copias ejecutables del
nucleo.

La Fase 6 de voz sigue abierta. La integración conserva el contrato
`canal -> Atlas Core -> ConversationManager -> AI Router -> respuesta -> TTS`,
de forma que STT, Telegram y TTS no conocen modelos físicos.

## Estado inicial y problemas corregidos

- Había seis copias de trabajo del núcleo con cambios útiles repartidos y una
  copia anidada adicional.
- El supervisor vigente había sido sustituido parcialmente por una versión
  antigua, lo que causaba tres errores de colección en la suite inicial.
- Faltaban aliases naturales de modo de respuesta y consulta de estado.
- El texto destinado a TTS conservaba Markdown, URL, emojis y puntuación que el
  motor podía verbalizar de forma artificial.
- Las preguntas breves y metaconversacionales podían recibir rodeos o falsas
  experiencias personales del modelo.
- Persistían estados, memoria personal, identidad y WAV de ejecución en el
  índice Git. Se mantienen en disco, pero se retiran del código publicable.
- La documentación operativa de STT y multimedia señalaba worktrees antiguos.

## Arquitectura consolidada

- Roles locales definitivos: `fast=qwen2.5:7b`,
  `reasoning=qwen2.5:14b` y `deep=qwen3:30b` mediante Ollama.
- `external` permanece deshabilitado y sin API.
- `ConversationManager` es común a CLI, Telegram y voz y separa identidad,
  interlocutor, domicilio, ubicación temporal y presencia.
- El router combina intención, contexto, referencias, ambigüedad, memoria,
  relaciones, herramientas, temporalidad, criticidad y volumen recuperado.
- El fallback escala solo ante insuficiencia verificable; nunca convierte falta
  de datos en permiso para inventar.
- Las fuentes verificadas y los resultados reales de herramientas prevalecen
  sobre la inferencia del modelo.
- Decisión estructurada y redacción con personalidad son fases independientes.

## Conversación y voz

- Se añadieron aliases claros para `modo texto`, `modo voz`, `modo automático`
  y consultas como `estado voz`.
- Los mensajes de espera solo se activan a partir de cuatro segundos.
- La salida hablada elimina Markdown, emojis y URL crudas, y convierte la
  puntuación estructural en pausas sin enviarla literalmente al motor.
- Kokoro registra preparación, síntesis, conversión, reproducción y total.
- Se implementó un puente persistente opcional, pero el benchmark local mostró
  peor latencia; por ello `ATLAS_KOKORO_PERSISTENT=false` es el valor seguro.
- Las respuestas solicitadas como frase breve se limitan de forma literal y el
  prompt prohíbe fingir vivencias, recuerdos o preferencias humanas.

## Evidencia

- Línea base anterior a la consolidación: tres errores de colección por el
  contrato antiguo de monitorización.
- Suite final: 1.172 pruebas aprobadas, 1 omitida y 2.324 subpruebas aprobadas
  en 159,91 segundos.
- Regresión operativa enfocada: 67 pruebas aprobadas.
- Benchmark del router: 16/16.
- Conversación controlada: 17/17.
- Modelos reales: 3/3 respuestas válidas; fast 9,797 s, reasoning 26,722 s y
  deep 88,885 s, descargando cada modelo de memoria después de usarlo.
- TTS: síntesis puntual aproximada 7,8 s; conversión a OGG alrededor de 96 ms;
  el modo persistente experimental fue más lento, alrededor de 14,8 s.
- Los hashes SHA-256 de identidad, continuidad y memoria semántica no cambiaron
  durante la suite completa.
- El arranque real dejó de registrar falsos encuentros al cambiar de contexto
  interno en Telegram, y la sincronización semántica sin cambios dejó de
  reescribir únicamente el sello temporal.
- La monitorización real resuelve los procesos desde los estados vigentes de
  Telegram y escritorio; Atlas, Telegram, monitor, widgets, Home Assistant y
  Ollama quedaron en estado correcto.

Los artefactos reproducibles están en `docs/evidence/` y los ejecutores en
`scripts/run_ai_benchmark.py`, `scripts/run_controlled_ai_conversation.py`,
`scripts/run_live_model_benchmark.py` y `scripts/run_tts_latency_benchmark.py`.

## Material de voz y siguiente paso

La evidencia completa de Ronda B se sincronizó, sin borrar los originales, en
`Atlas Project/12 - Voz/07 - Pruebas y resultados/Pruebas/` con 324 archivos,
66.889.416 bytes y verificación SHA-256 sin diferencias.

La continuación correcta de la Fase 6 es la escucha ciega humana de la Ronda B.
Solo después de esa decisión debe integrarse el motor seleccionado mediante el
contrato TTS sustituible de Atlas Core. Esta consolidación no declara una voz
ganadora ni cierra la Fase 6.

## Límites y operación real

No se envió ningún mensaje a usuarios, no se ejecutó ninguna acción doméstica,
no se realizó búsqueda web real y no se configuró ningún proveedor externo de
IA. Las rutas y permisos se validaron con dobles seguros. Los comandos reales de
Telegram deben ser enviados por el usuario autenticado para probar autorización
de extremo a extremo.
