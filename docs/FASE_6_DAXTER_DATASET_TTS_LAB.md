# Fase 6 — cierre del dataset Daxter y laboratorio TTS

Estado vigente (11 de agosto de 2026): dataset cerrado y validado; Ronda B resuelta con B1; las 38 evaluaciones emocionales y las 40 revisiones de personalidad están procesadas. PersonalityAdapter v2, TTS B1 local, STT local y el turno manual de voz para PC están integrados con fallback textual. No hay escucha continua ni wake-word.

## Evidencia del dataset

La auditoría se ejecutó contra el maestro de 1.300 filas y los WAV originales de `02_limpios`. El CSV maestro no se modificó y su SHA-256 es:

```text
cc461a9e38e4ec13d9a80b726d5b9c6572a6b4a47eff293ea018d23d6cbc5f13
```

Resultados:

- 1.300 muestras y 1.300 identificadores únicos;
- 1.300 WAV legibles y 1.300 hashes coincidentes;
- 49 min 12,479 s de audio;
- 0 errores, 2 avisos y 7 muestras marcadas para revisión;
- 0 grupos de duplicados exactos y 0 candidatos acústicos duplicados;
- 1.300 muestras marcadas como utilizables para TTS.

La herramienta `tools/audit_daxter_dataset.py` genera el informe completo, las excepciones, estadísticas, manifiesto y sumas SHA-256. Rechaza un cierre si cambia el número esperado de filas, el hash del maestro, falta un WAV, un archivo no es PCM legible o no coincide su hash.

Ejemplo reproducible:

```powershell
python tools/audit_daxter_dataset.py `
  --metadata <metadata_daxter_final.csv> `
  --audio-root <02_limpios> `
  --output-dir <auditoria_1060> `
  --expected-rows 1300 `
  --expected-metadata-sha256 cc461a9e38e4ec13d9a80b726d5b9c6572a6b4a47eff293ea018d23d6cbc5f13
```

Los clips más largos y los dos extremos con silencio quedan visibles en `AUDIO_AUDIT_EXCEPTIONS.csv`; no se han descartado automáticamente ni se ha cambiado su transcripción.

## Referencias de voz

El manifiesto selecciona nueve referencias de Jak II con distintas emociones y calidad disponible `buena`. La referencia combinada de laboratorio concatena tres de ellas —neutral, emocionada y asustada— en un WAV mono de 48 kHz y 12,36 s. Esta selección es evidencia para las pruebas, no una modificación del dataset.

## Ronda A local

La batería común contiene trece frases en español: neutra, sonriente, traviesa, sorprendida, emocionada, asustada, enfadada, curiosa, confiada, determinada, juguetona, números y nombres, y una frase larga. Los motores se ejecutaron en Windows 11 con una RTX 4060:

| Motor | Modalidad | Salidas | Frecuencia | RTF medio | VRAM pico | Similitud ECAPA media |
|---|---|---:|---:|---:|---:|---:|
| Chatterbox Multilingual 0.1.7 | clonación zero-shot | 13/13 | 24 kHz | 1,225 | 4.529,9 MB | 0,69232 |
| Chatterbox + OpenVoice V2 | TTS y conversión de voz | 13/13 | 22,05 kHz | 0,165 | 717,8 MB | 0,65335 |

Todas las salidas son WAV mono PCM de 16 bits. La métrica ECAPA es orientativa y no sustituye la escucha. Chatterbox produjo duraciones anómalas en los casos `09_confiado` y `12_numeros_nombres`; deben escucharse para detectar pausas, repetición o alucinación. OpenVoice usa esas mismas tomas como fuente y puede heredar el problema.

La evaluación humana de Ronda A dio a Chatterbox una media de 4,4066/5 y una similitud con Daxter de 4,6154/5, frente a 4,0989 y 3,5385 de Chatterbox + OpenVoice. REDACTED_2c7b6821719d seleccionó Chatterbox Multilingual V2 como motor base de Ronda B. OpenVoice se conserva como alternativa experimental, sin borrar sus salidas.

Chatterbox gana por identidad vocal, emoción y naturalidad percibidas, además de funcionamiento completamente local. Sus problemas conocidos son el acento latinoamericano ocasional, pronunciación de nombres, posibles cortes/alucinaciones, agudeza y roboticidad en frases largas. En la ejecución local usó Python 3.11, PyTorch 2.6.0+cu124 y una RTX 4060; la Ronda A alcanzó 4.529,9 MB de VRAM y RTF medio 1,225. El código es MIT y las salidas incluyen la marca de agua PerTh. La ausencia de locale `es-ES` y de entrenamiento oficial son riesgos explícitos, no capacidades supuestas.

## Dataset específico de Ronda B

`tools/prepare_chatterbox_dataset.py` deriva manifests sin modificar el maestro ni copiar o reescribir los WAV. Conserva todas las columnas humanas, la ruta y hash originales, y añade sólo estado de preparación, split, grupo textual y seed.

| Estado/split | Muestras | Minutos |
|---|---:|---:|
| train | 1.009 | 36,2625 |
| validation | 127 | 4,6047 |
| test | 127 | 4,6354 |
| review, sin split | 36 | — |
| excluded | 1 | — |

La seed es `20260809`. Los textos iguales o casi iguales se agrupan antes del reparto; se detectaron 1.241 grupos y cero fugas de un grupo entre splits. Los 36 clips en revisión incluyen avisos de auditoría, calidad `aceptable` o duración inferior a 0,75 s. La única exclusión es `daxter_1182_jakx_dax110r`, conservada con motivo explícito `quality_limite`.

## Soporte real de Chatterbox

Se inspeccionó el paquete `chatterbox-tts 0.1.7`, su API instalada y el commit oficial `5de7a54aa4e5e2baadb0182dde554908b48b85c2`. El repositorio no publica scripts, cargador de dataset ni pipeline estable de fine-tuning. Por ello no se han inventado checkpoints entrenados.

La adaptación ligera usa únicamente controles reales: `language_id="es"`, referencia de audio, `exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`, `min_p` y `top_p`. V2 no expone locale `es-ES`, diccionario fonético ni phonemizer configurable. La referencia española es por tanto el principal control de acento. Fuentes oficiales: [repositorio Chatterbox](https://github.com/resemble-ai/chatterbox) y [API multilingual](https://github.com/resemble-ai/chatterbox/blob/master/src/chatterbox/mtl_tts.py).

## Ronda B local

Cada candidato contiene 13 casos originales y 21 corregidos/objetivo, 34 WAV por candidato y 136 en total:

| Candidato | Configuración | ECAPA original | ECAPA corregida | RTF corregido | VRAM pico corregida |
|---|---|---:|---:|---:|---:|
| B0 | baseline exacto de Ronda A; correcciones sin normalizador | 0,69232 | 0,63570 | 1,0128 | 3.708,8 MB |
| B1 | referencia diversa + normalización de inferencia | 0,69019 | 0,68769 | 1,0386 | 3.713,2 MB |
| B2 | referencia española con nombres + CFG 0,30 | 0,67866 | 0,65674 | 1,0252 | 3.722,3 MB |
| B3 | referencia dinámica por emoción | 0,56187 | 0,51691 | 1,0485 | 3.478,6 MB |

ECAPA no decide la ronda: no mide español de España, pronunciación, emoción o naturalidad. B0 conserva las anomalías históricas de `09_confiado` y `12_numeros_nombres`; su batería corregida no muestra esas banderas. B2/corregida marca `04_sorprendido` por duración anómala y B3 reduce claramente la similitud automática, por lo que todos deben escucharse sin revelar identidad.

B1–B3 prueban una capa sólo de inferencia —Jak→Yak, Atlas→Átlas, Daxter→Dákster, Home Assistant→Joum Asístent y Telegram→Télegram— y verbalización de números conocidos. Son hipótesis acústicas reversibles; `metadata_daxter_final.csv` permanece intacto.

El laboratorio `voice_lab_round_b` incluye `BLIND_LISTENING_PLAYER.html`, 136 copias de audio con nombres ciegos, `HUMAN_LISTENING_TEST_ROUND_B.csv`, `BLIND_KEY.json`, métricas, incidencias y sumas SHA-256.

## Cierre humano de Ronda B

Las 136 muestras fueron puntuadas en las nueve dimensiones previstas. La clave ciega se cruzó mediante `blind_code` sin alterar el CSV humano (`SHA-256 00f54cb95bffc8be670b65272b41490c5a41b42c9719d90fde49b7f74dfb30ba`).

| Candidato | Media global | Similitud global | Media corregida | Similitud corregida | Pronunciación corregida | Inicio corregido |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 4,3529 | 4,0882 | 4,3757 | 4,0952 | 4,3810 | 4,6190 |
| B1 | **4,4347** | **4,0882** | **4,4815** | **4,2381** | 4,6667 | 4,9048 |
| B2 | 4,2222 | 3,7647 | 4,2222 | 3,7143 | 4,7143 | 5,0000 |
| B3 | 4,3660 | 3,4412 | 4,3439 | 3,3333 | 4,7619 | 4,9524 |

B1 gana porque lidera simultáneamente similitud y media humana en la batería corregida, conserva la similitud global de B0, mejora pronunciación/inicios y mantiene cero anomalías automáticas corregidas. B0 queda segundo: conserva ventajas de naturalidad y emoción en la batería original, pero rinde peor en los casos operativos corregidos.

El perfil reproducible se congela en `voice_profiles/daxter_es_jak2.json`: Chatterbox Multilingual V2 0.1.7, referencia diversa Jak II, `language_id="es"`, CFG 0,35, temperatura 0,8, penalización de repetición 2,0, `min_p=0,05` y `top_p=1,0`. Continúa siendo conditioning/inferencia; no existe ni se declara un checkpoint entrenado.

Normalizaciones aceptadas:

- `Jak→Yak`: en tres casos mejora todas las dimensiones prioritarias frente a B0;
- verbalización de fechas y números: en la comparación original eleva inteligibilidad 2→4, pronunciación 1→4 y español de España 1→4.

Normalizaciones rechazadas:

- `Atlas→Átlas`: empeora pronunciación y español de España; el Atlas aislado de B0 obtuvo 5/5;
- `Home Assistant→Joum Asístent` y `Telegram→Télegram`: no mejoran el caso técnico y reducen similitud;
- `Daxter→Dákster`: no existe comparación humana directa, por lo que no se acepta sin evidencia.

Los resultados completos están en `ROUND_B_HUMAN_RESULTS.json`, `ROUND_B_HUMAN_RESULTS.md` y `ROUND_B_FINAL_DECISION.json` dentro del laboratorio local.

## Cierre humano del sistema emocional

Las 38 filas puntuadas de `HUMAN_EMOTION_TEST.csv` se cruzaron con la clave ciega sin alterar la fuente (`SHA-256 d163d1ff99ed66fe15f9feb3ebe0666a3308254544c1c4c968bebd48b200e02e`). B1 con referencia diversa obtuvo 3,9130 en identidad, frente a 2,8000 de la estrategia experimental. La evaluación humana deja 7 emociones aprobadas (`neutral`, `picaro`, `sorprendido`, `emocionado`, `confiado`, `determinado`, `risa`), 7 en ajuste dirigido y `sonoliento` en fallback.

`sonoliento` no hereda ya evidencia ficticia de `cansado`: hasta una comparación humana directa usa `neutral` baja. Las otras emociones no aprobadas también caen de forma segura a neutral. `EMOTION_MINI_ROUND_PLAN.json` limita la comprobación posterior a 16 WAV ciegos como máximo —dos por cada una de las ocho emociones— y exige 4/5 en identidad, emoción y naturalidad sin artefactos graves.

`voice_profiles/DAXTER_EMOTION_CATALOG_FINAL.json` es el catálogo operativo. Conserva las quince expresiones oficiales, el estado humano de cada una y el fallback explícito; una ausencia de anomalías automáticas nunca equivale a aprobación.

La capa `VoiceStyleSelector` resuelve emoción, intensidad, energía y fallbacks sin conocer el proveedor. `ChatterboxStyleAdapter` traduce después ese estilo a los únicos controles reales de V2. El fallo de referencia vuelve a la referencia diversa ganadora.

El laboratorio `voice_lab_emotions` contiene 38 WAV ciegos: dos estrategias de referencia para cada emoción y calibraciones baja/alta en neutral, emocionado, asustado y travieso. Los 38 son PCM mono de 16 bits y, tras conservar y repetir tres intentos anómalos, no quedan avisos automáticos en las muestras seleccionadas. Para risa se sintetiza sólo una interjección breve; no se inventa una carcajada larga.

La primera ejecución refrescó la caché oficial de Chatterbox desde Hugging Face antes de generar. No se subieron datos ni audios. El runner fuerza ahora `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`; las repeticiones verificadas usaron sólo la caché local.

## Personalidad conversacional v2

El análisis de las 1.300 transcripciones está en `docs/DAXTER_PERSONALITY_ANALYSIS.md` y el perfil estructurado en `conversation/profiles/DAXTER_PERSONALITY_PROFILE.json`. El dataset respalda, entre otros, entusiasmo, impulsividad, dramatismo, lealtad, humor, ingenio, queja, fanfarronería, burla, sarcasmo, curiosidad y afecto; cada rasgo conserva conteo y `sample_id` de evidencia.

Las 40 revisiones se procesaron sin alterar el CSV humano (`SHA-256 5388a081482ab1a5f428536586f4fb37be60938988a8eb6aa0565c61dd27507c`). La media fue 4,25 en identidad Daxter, 4,40 en naturalidad, 4,55 en humor, 4,475 en intensidad y 5,0 en conservación de información. `normal` queda como nivel predeterminado; `low` mantiene una microidentidad verbal cuando el contexto no es sensible; `high` permite un único remate contextual. Privacidad, seguridad, conducción y emergencia fuerzan salida sobria sin humor.

`PersonalityAdapter` v2 usa reglas, tipo de respuesta, canal, emoción, intensidad, historial inmediato y transformaciones estructurales limitadas. Las correcciones de REDACTED_f73137d930c3 se convirtieron en patrones —unión natural de cláusulas cortas, aperturas contextuales, menos repetición y coherencia entre léxico y emoción—, no en un banco de frases. No reproduce diálogos del dataset.

`BaseResponse` separa texto factual, hechos, resultado de acción, incertidumbre, permisos y errores. `StyledResponse` contiene la presentación posterior. `FactPreservationValidator` rechaza una adaptación que pierda cifras, nombres o marcadores protegidos y vuelve determinísticamente al texto base. La misma `DaxterResponsePipeline` sirve CLI, Telegram y voz, con independencia de Ollama o de futuros proveedores.

Los resultados completos están en `PERSONALITY_HUMAN_RESULTS.json` y `.md` dentro del laboratorio local; las reglas versionadas están en `conversation/profiles/DAXTER_PERSONALITY_RULES_V2.json`.

## TTS, STT y turno manual de PC

`BaseTTSProvider` sigue siendo el contrato común. `ChatterboxDaxterProvider` lee el perfil B1 congelado, inicia un worker persistente de Python 3.11 sólo al primer uso, fuerza modo offline y usa una caché cuya clave incluye texto normalizado, voz, emoción, intensidad y versión. `VoiceService` resuelve Daxter B1, luego un TTS español local alternativo configurado y finalmente texto. La cola y el reproductor exponen `stop_current_audio()` y `clear_queue()`.

La prueba real generó un WAV B1 en 69.021 ms incluyendo carga inicial y recuperó la misma solicitud en 11 ms desde caché. Los WAV y la caché viven en `runtime/voice/`, fuera de Git.

`BaseSTTProvider` y `FasterWhisperSTTProvider` reutilizan el modelo local `faster-whisper-small`: ofrece buen equilibrio para español y cabe en el PC objetivo; usa CUDA si el entorno compatible está disponible y cae a CPU `int8`. Nunca descarga modelos salvo habilitación explícita. En la prueba local CPU transcribió «Apaga atlas.» en 6.286 ms, con confianza de habla media; la orden sensible quedó en espera de confirmación y `Atlas.process` no fue llamado.

Telegram `voice` y `audio` pasan por el mismo `AudioConverter` y `STTService`; no existe una segunda lógica STT. Los temporales se borran tras el turno. En PC, `tools/run_daxter_voice_pc.py` graba exclusivamente entre dos pulsaciones de Enter, muestra latencias de grabación, STT, Atlas, personalidad, TTS y total, y conserva texto si la voz falla.

```powershell
python tools/run_daxter_voice_pc.py --list-devices
python tools/run_daxter_voice_pc.py --device "Nombre exacto de los cascos Bluetooth"
```

Variables necesarias: `ATLAS_CHATTERBOX_PYTHON`, `ATLAS_DAXTER_VOICE_LAB_ROOT` y `ATLAS_STT_MODEL_PATH`; `.env.example` documenta todas sin incluir rutas privadas.

La arquitectura móvil futura será aplicación → detector local «Oye Daxter» → grabación → Atlas. No se transmitirá audio continuo: sólo el fragmento capturado después del wake-word. Esa escucha y el barge-in automático no están implementados en esta intervención.

## Límites y seguridad

- El dataset, las referencias, los modelos y los WAV generados permanecen locales y están excluidos por `.gitignore`.
- La integración es reversible y desacoplada; cualquier fallo de STT/TTS conserva el canal textual y no bloquea Atlas.
- No se aceptaron en nombre del usuario licencias o términos adicionales; por ello XTTS-v2 no se ejecutó.
- B1 sigue siendo el ganador; la personalidad está validada y el catálogo emocional conserva estados y fallbacks humanos por emoción.
- El intento inicial contra `04_normalizados` se conserva separado como evidencia de raíz inválida; sus hashes no correspondían al maestro de 48 kHz.

## Verificación del código

Las pruebas cubren la aceptación del dataset válido, el rechazo de hash incorrecto, la batería común y las utilidades WAV. La validación de entrega incluye pruebas focalizadas, colección completa, suite completa, compilación y comprobación final del estado de Git y del hash del maestro.
