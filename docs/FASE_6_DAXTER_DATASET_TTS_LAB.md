# Fase 6 — cierre del dataset Daxter y laboratorio TTS

Estado: dataset cerrado; Ronda B resuelta por evaluación humana con B1 como configuración base ganadora; catálogo emocional y personalidad v1 construidos, ambos pendientes de validación humana. No se ha integrado de forma irreversible ninguna voz o personalidad en Atlas.

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

## Sistema emocional provisional

`voice_profiles/DAXTER_EMOTION_CATALOG.json` contiene las quince expresiones oficiales y sus estadísticas reales. El maestro aporta evidencia directa para catorce; `sonoliento` tiene cero muestras y cae de forma explícita a `cansado`. La intensidad usa un único eje parametrizado: 0,45 baja, 0,55 media y 0,65 alta; los extremos proceden de B1 y el punto medio queda pendiente de escucha.

La capa `VoiceStyleSelector` resuelve emoción, intensidad, energía y fallbacks sin conocer el proveedor. `ChatterboxStyleAdapter` traduce después ese estilo a los únicos controles reales de V2. El fallo de referencia vuelve a la referencia diversa ganadora.

El laboratorio `voice_lab_emotions` contiene 38 WAV ciegos: dos estrategias de referencia para cada emoción y calibraciones baja/alta en neutral, emocionado, asustado y travieso. Los 38 son PCM mono de 16 bits y, tras conservar y repetir tres intentos anómalos, no quedan avisos automáticos en las muestras seleccionadas. Para risa se sintetiza sólo una interjección breve; no se inventa una carcajada larga.

La primera ejecución refrescó la caché oficial de Chatterbox desde Hugging Face antes de generar. No se subieron datos ni audios. El runner fuerza ahora `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`; las repeticiones verificadas usaron sólo la caché local.

## Personalidad conversacional v1

El análisis de las 1.300 transcripciones está en `docs/DAXTER_PERSONALITY_ANALYSIS.md` y el perfil estructurado en `conversation/profiles/DAXTER_PERSONALITY_PROFILE.json`. El dataset respalda, entre otros, entusiasmo, impulsividad, dramatismo, lealtad, humor, ingenio, queja, fanfarronería, burla, sarcasmo, curiosidad y afecto; cada rasgo conserva conteo y `sample_id` de evidencia.

`PersonalityAdapter` conserva literalmente la respuesta base de Atlas y sólo añade una marca breve original cuando el contexto lo permite. Privacidad, seguridad, conducción y emergencia fuerzan personalidad `low`; hechos, cifras, permisos, incertidumbre y resultado de acciones nunca se reescriben. No se usa el banco de diálogos del juego como motor y no se ha entrenado ningún LLM.

El laboratorio `personality_lab` contiene 40 situaciones offline con respuesta base, respuesta Daxter, emoción, intensidad y nivel efectivo. La evaluación humana permanece vacía y separada de la escucha emocional.

## Límites y seguridad

- El dataset, las referencias, los modelos y los WAV generados permanecen locales y están excluidos por `.gitignore`.
- Los scripts no integran aún ningún motor en Atlas y no cambian su fallback de voz.
- No se aceptaron en nombre del usuario licencias o términos adicionales; por ello XTTS-v2 no se ejecutó.
- B1 es el ganador reproducible de Ronda B; siguen pendientes la escucha
  emocional ciega y la revisión humana de personalidad, por lo que no se
  declara integrado el sistema definitivo ni cerrada la Fase 6.
- Atlas Core incorpora un router local `fast`/`reasoning`/`deep`, transparente
  para STT y TTS. La voz continúa enviando texto al mismo núcleo y no conoce el
  modelo físico seleccionado; el fallback de voz no repite la acción del Core.
- El intento inicial contra `04_normalizados` se conserva separado como evidencia de raíz inválida; sus hashes no correspondían al maestro de 48 kHz.

## Verificación del código

Las pruebas cubren la aceptación del dataset válido, el rechazo de hash incorrecto, la batería común y las utilidades WAV. La validación de entrega incluye pruebas focalizadas, colección completa, suite completa, compilación y comprobación final del estado de Git y del hash del maestro.
