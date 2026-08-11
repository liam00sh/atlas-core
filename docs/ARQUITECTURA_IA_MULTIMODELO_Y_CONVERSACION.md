# Arquitectura de IA multimodelo y conversación

Estado: implementada en la rama `feature/ai-conversation-router`.

## Principio ejecutivo

La IA interpreta y razona; Atlas gobierna la verdad, los permisos y las
acciones. Ninguna salida del modelo sustituye identidades autenticadas,
relaciones verificadas, memoria autorizada, estado de herramientas ni el
resultado real de una acción.

## Roles locales

| Rol | Proveedor | Modelo inicial | Uso |
|---|---|---|---|
| `fast` | Ollama | `qwen2.5:7b` | conversación simple y redacción breve |
| `reasoning` | Ollama | `qwen2.5:14b` | contexto, memoria, ambigüedad y varios pasos |
| `deep` | Ollama | `qwen3:30b` | contradicciones o contexto grande |
| `external` | deshabilitado | ninguno | reserva arquitectónica futura |

Los nombres físicos están centralizados en `ai/models/roles.py` y pueden
sobrescribirse mediante `ATLAS_AI_FAST_MODEL`, `ATLAS_AI_REASONING_MODEL` y
`ATLAS_AI_DEEP_MODEL`. `ATLAS_AI_ROUTE` admite `auto`, `fast`, `reasoning` y
`deep`. No existe configuración de API externa en esta fase.

## Router, validación y fallback

`AIRouter` combina intención, mensajes de contexto, referencias pronominales,
ambigüedad, memoria, relaciones, temporalidad, pasos, herramientas,
criticidad, cantidad recuperada, contradicciones y posibilidad determinista.
No ejecuta todos los modelos: comienza en el nivel elegido y solo asciende si
la validación estructural lo permite.

`ResponseValidator` comprueba respuesta vacía, idioma inesperado, repetición,
datos requeridos ausentes y afirmaciones de acciones no confirmadas. Un modelo
mayor no recibe permiso para inventar un dato que no existe. Los logs usan el
formato `[AI ROUTER] route=... reason=... model=... fallback=...` y nunca
guardan chain-of-thought.

## Estado conversacional

`ConversationManager` mantiene estado por canal, sesión y usuario autenticado:
interlocutor, tema, entidades, referencias, ubicación contextual, domicilio
habitual, ubicación temporal, presencia doméstica, tiempo relevante, acciones,
confirmaciones, herramientas, hechos temporales y participantes compartidos.

Identidad, cuenta, domicilio, ubicación temporal y presencia son campos
independientes. «Estoy en casa de Alex» puede actualizar el contexto de lugar,
pero no cambia identidad, domicilio, parentescos ni permisos de Home Assistant.

## Fuentes de verdad

La prioridad ejecutable es:

1. estado confirmado por herramientas;
2. datos personales verificados;
3. identidad y permisos autenticados;
4. contexto activo;
5. memoria persistente autorizada;
6. web autorizada;
7. inferencia del modelo.

Una inferencia aislada no se considera información suficiente. Los conflictos
de igual autoridad requieren aclaración.

## Decisión y redacción

`AtlasDecision` separa acción, autorización, ejecución, entidad, estado y
motivo. `DecisionResponseComposer` solo redacta después de recibir la decisión.
La personalidad puede envolver un error, pero la primera frase debe indicar qué
falló y por qué. Home Assistant registra la decisión estructurada antes de
mostrar el mensaje y nunca afirma éxito sin confirmación del adaptador.

## Mensajería y latencia

Los eventos se redactan con composición contextual por usuario, hora, canal,
situación y asistente. Se conserva un historial reciente y un ID de evento: dos
emisiones del mismo arranque se deduplican, mientras que un reinicio real crea
otro ID. Telegram solo muestra progreso tras 4,5 segundos reales; saludos y
comandos rápidos no muestran espera.

## Benchmark

`tests/ai_benchmark/` cubre comandos simples, contexto, identidad, ubicación
temporal, parentescos, memoria, ambigüedad, Home Assistant, web, routing y
prevención de alucinaciones. `scripts/run_ai_benchmark.py` genera un JSON con
rol, modelo, fallback, latencia, resultado, razón resumida, memoria,
herramientas y web, sin razonamiento privado.

## Voz

La integración permanece:

`audio -> STT -> Atlas Core -> ConversationManager -> AIRouter -> respuesta -> TTS`

STT, TTS y Telegram no conocen el modelo físico. La voz mantiene permisos,
identidades, memoria, confirmaciones y auditoría del texto. El fallback de voz
solo cambia la entrega y no repite Atlas Core ni una acción ya procesada. La
Fase 6 continúa abierta; esta mejora no selecciona ni cierra la voz de Daxter.

