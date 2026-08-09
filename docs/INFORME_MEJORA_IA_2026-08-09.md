# Informe de mejora de IA y conversación

## Estado inicial y punto de restauración

- Copia vigente encontrada: `C:\Proyectos\Atlas\atlas_core_ogg_fix`, rama
  `fase-6-daxter-tts-lab`, commit `44cb205`. La copia histórica de Drive estaba
  atrasada y contenía cambios ajenos, por lo que no se modificó.
- Trabajo realizado en un worktree limpio:
  `C:\Proyectos\Atlas\atlas_core_ai_router`, rama
  `feature/ai-conversation-router`.
- Backup Git completo y verificado:
  `C:\Proyectos\Atlas\backups\atlas-fase6-pre-ai-2026-08-09-44cb205.bundle`.
- Línea base: 1.081 pruebas pasadas, 1 omitida y 2.324 subpruebas pasadas.
- Los hashes de `people.json`, `animals.json` y `relationships.json` se
  mantuvieron sin cambios.

## Problemas reproducidos

- El modelo físico estaba acoplado a una ruta principal y no existían roles
  definitivos ni fallback local.
- El historial textual no representaba explícitamente identidad, domicilio,
  ubicación temporal y presencia doméstica como conceptos independientes.
- Una aclaración pendiente de localidad podía capturar una petición posterior
  no relacionada.
- Algunas decisiones de Home Assistant se inferían desde el texto de la
  respuesta; ahora la ejecución exige confirmación estructurada.
- Los avisos de ciclo de vida dependían de bancos de frases completas y el
  progreso podía aparecer antes de una latencia apreciable.
- La inicialización del índice semántico no disponía de una ruta de datos
  aislable; se añadió `ATLAS_KNOWLEDGE_DATA_DIR` y se verificó que el arranque
  de prueba no modifica el índice real.

## Arquitectura implementada

- Registro central de roles `fast`, `reasoning`, `deep` y `external`.
- `external` está deshabilitado por construcción y sin API configurada.
- Router explicable con señales combinadas, override manual y selección
  determinista cuando Atlas ya puede resolver la petición.
- Runtime local lazy con fallback ascendente y validación estructural.
- `ConversationManager` compartido por CLI, Telegram y la futura voz.
- Jerarquía ejecutable de fuentes de verdad.
- Contrato `AtlasDecision` separado de la redacción.
- Qwen3 entrega solo el campo final de Ollama; la deliberación privada se
  mantiene separada y no se registra.
- Mensajes contextuales, historial anti-repetición y deduplicación por ID de
  evento. El progreso de Telegram no aparece antes de 4,5 segundos reales.

## Modelos locales

| Rol | Modelo | Tamaño local | Prueba sintética |
|---|---|---:|---|
| fast | `qwen2.5:7b` | 4,7 GB | `OK`, 9,25 s |
| reasoning | `qwen2.5:14b` | 9,0 GB | `OK`, 187,61 s en arranque en frío |
| deep | `qwen3:30b` | 18 GB | `OK`, 644,69 s; 313 caracteres de thinking separados |

Los modelos se probaron uno a uno y se descargaron de memoria entre pruebas.
El modelo deep funciona, pero en este equipo reparte 19 GB entre CPU y GPU y
su latencia en frío es alta; por eso solo debe usarse para casos realmente
complejos. Quedaron aproximadamente 314 GB libres tras las descargas.

## Pruebas y benchmark

- Colección final: 1.116 pruebas.
- Suite final: 1.115 pasadas, 1 omitida, 2.324 subpruebas pasadas, 0 fallos.
- Benchmark de rutas: 16/16 casos correctos.
- Conversación controlada: 17/17 resultados correctos.
- Arranque aislado: correcto; roles `fast,reasoning,deep`; `external=False`;
  hash del índice de conocimiento sin cambios.
- No hubo Telegram real, Home Assistant real, búsqueda web real, mensajes a
  terceros ni acciones destructivas.

Evidencias:

- `docs/evidence/pytest_baseline_2026-08-09.xml`
- `docs/evidence/pytest_final_2026-08-09.xml`
- `docs/evidence/atlas_ai_benchmark_2026-08-09.json`
- `docs/evidence/controlled_ai_conversation_2026-08-09.json`

## Conversación final controlada

Resultados representativos:

- `¿Quién soy?` -> identifica a REDACTED_bc04a68d9192 desde el perfil autenticado.
- `¿Quiénes son mis primos?` -> usa relaciones verificadas y no convierte a
  REDACTED_2c7b6821719d en primo.
- `He venido a casa de REDACTED_2c7b6821719d unos días` -> conserva ubicación temporal sin
  cambiar identidad, domicilio ni permisos.
- `¿Dónde estoy ahora?` -> responde `casa de REDACTED_2c7b6821719d` como contexto temporal.
- `¿Dónde vivo?` -> responde REDACTED_4cde1bf18b9c como domicilio habitual.
- `Apaga la luz del acuario pequeño` -> deniega por presencia no verificada y
  nunca afirma que la luz se apagó.
- `¿Cuál es la población actual de REDACTED_a77d7bb7adbf?` -> reconoce que falta un dato
  verificado y ofrece consulta web sin ejecutarla.
- Overrides `fast`, `reasoning` y `deep` -> rutas verificadas.
- Fallback -> `fast -> reasoning` tras una respuesta vacía simulada.
- Mensaje a otro usuario -> cola simulada, sin entrega externa.
- Cuatro avisos de disponibilidad -> cuatro formulaciones distintas.

## Archivos principales creados

- `ai/models/roles.py`
- `ai/routing/router.py`, `runtime.py` y `validator.py`
- `conversation/manager.py` y `event_messages.py`
- `core/decisions.py`
- `knowledge/truth.py`
- `ai/benchmark.py`
- `scripts/run_ai_benchmark.py`
- `scripts/run_controlled_ai_conversation.py`
- `tests/ai_benchmark/` con todas las categorías solicitadas
- `docs/ARQUITECTURA_IA_MULTIMODELO_Y_CONVERSACION.md`
- evidencias de pruebas y conversación en `docs/evidence/`

## Archivos principales modificados

- Integración central: `main.py`, `core/atlas.py`, `core/atlas_ai.py` y
  `core/atlas_daily.py`.
- Modelos: `ai/models/model_registry.py` y
  `ai/providers/ollama_provider.py`.
- Verdad y recuperación: `knowledge/retriever.py`.
- Acciones: `automation/home_intent_service.py`.
- Telegram: `telegram_interface/lifecycle.py` y `progress.py`.
- Configuración, README, aislamiento de pytest y pruebas relacionadas.
- Documentación local de arquitectura y Fase 6.

## Documentación oficial actualizada

Se añadieron secciones verificadas, sin reemplazar contenido previo, en:

- `01 - Especificación y Arquitectura`
- `06 - Changelog`
- `16 - Roadmap del Proyecto Atlas`
- `21 - Manual de IA local, prompts y contexto`
- `22 - Manual de pruebas, persistencia y mantenimiento`
- `37 - Arquitectura técnica modular de la Fase 6 - Voz`

## Pendientes y continuación de voz

- La latencia en frío de `reasoning` y, sobre todo, `deep` debe medirse con
  conversaciones reales antes de fijar umbrales definitivos del router.
- El benchmark actual valida rutas y contratos con proveedores simulados; debe
  ampliarse gradualmente con evaluación humana de calidad de respuestas.
- No se ha publicado ni abierto PR; los cambios permanecen en la rama local de
  trabajo para revisión.
- La Fase 6 continúa desde la evaluación humana pendiente de los motores de voz.
  Tras esa decisión, la integración debe conectar STT/TTS con `Atlas.process()`
  y la respuesta final del núcleo. La voz no debe conocer roles ni modelos
  físicos.
