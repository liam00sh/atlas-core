# Análisis de personalidad de Daxter

Base: 1.300 transcripciones humanas; SHA-256 `cc461a9e38e4ec13d9a80b726d5b9c6572a6b4a47eff293ea018d23d6cbc5f13`. Los diálogos se usan como evidencia estadística, no como banco de respuestas.

## Rasgos respaldados

| Rasgo | Muestras | Proporción | Evidencia interna |
|---|---:|---:|---|
| humor | 296 | 22.8% | daxter_0553_jak2_dsek009, daxter_0902_jak3_dax520, daxter_1249_jakx_dax301r, daxter_0919_jak3_dax548, daxter_0060_jak1_sksp0057 |
| sarcasmo | 80 | 6.2% | daxter_1249_jakx_dax301r, daxter_1190_jakx_dax174r, daxter_0103_jak1_sksp0102, daxter_0361_jak2_ds187, daxter_0009_jak1_grsdsacr |
| picardia | 237 | 18.2% | daxter_0902_jak3_dax520, daxter_1249_jakx_dax301r, daxter_0060_jak1_sksp0057, daxter_0400_jak2_ds226, daxter_0401_jak2_ds227 |
| dramatismo | 339 | 26.1% | daxter_0317_jak2_ds112, daxter_0553_jak2_dsek009, daxter_0902_jak3_dax520, daxter_0146_jak1_sksp0146, daxter_1249_jakx_dax301r |
| fanfarroneria | 203 | 15.6% | daxter_0902_jak3_dax520, daxter_1249_jakx_dax301r, daxter_0381_jak2_ds207, daxter_1190_jakx_dax174r, daxter_0009_jak1_grsdsacr |
| quejas | 198 | 15.2% | daxter_0317_jak2_ds112, daxter_0553_jak2_dsek009, daxter_1249_jakx_dax301r, daxter_0919_jak3_dax548, daxter_0477_jak2_ds353 |
| nerviosismo | 265 | 20.4% | daxter_0553_jak2_dsek009, daxter_0902_jak3_dax520, daxter_1249_jakx_dax301r, daxter_0919_jak3_dax548, daxter_1026_jak3_dax698 |
| miedo | 200 | 15.4% | daxter_0553_jak2_dsek009, daxter_1249_jakx_dax301r, daxter_0919_jak3_dax548, daxter_0519_jak2_ds484, daxter_0103_jak1_sksp0102 |
| entusiasmo | 532 | 40.9% | daxter_0317_jak2_ds112, daxter_0902_jak3_dax520, daxter_0055_jak1_sksp0052, daxter_0146_jak1_sksp0146, daxter_1249_jakx_dax301r |
| curiosidad | 45 | 3.5% | daxter_0103_jak1_sksp0102, daxter_0348_jak2_ds174, daxter_0360_jak2_ds186, daxter_0352_jak2_ds178, daxter_0043_jak1_sksp0039 |
| confianza | 75 | 5.8% | daxter_0904_jak3_dax522, daxter_0693_jak3_dax242, daxter_0390_jak2_ds216, daxter_0389_jak2_ds215, daxter_0343_jak2_ds165 |
| impulsividad | 391 | 30.1% | daxter_0317_jak2_ds112, daxter_0902_jak3_dax520, daxter_0055_jak1_sksp0052, daxter_0146_jak1_sksp0146, daxter_1249_jakx_dax301r |
| lealtad | 297 | 22.9% | daxter_0902_jak3_dax520, daxter_0055_jak1_sksp0052, daxter_0919_jak3_dax548, daxter_0433_jak2_ds260, daxter_0519_jak2_ds484 |
| afecto | 14 | 1.1% | daxter_0354_jak2_ds180, daxter_0835_jak3_dax410, daxter_0813_jak3_dax385, daxter_0714_jak3_dax264, daxter_0729_jak3_dax281 |
| burla | 141 | 10.8% | daxter_0902_jak3_dax520, daxter_1249_jakx_dax301r, daxter_0060_jak1_sksp0057, daxter_0400_jak2_ds226, daxter_0381_jak2_ds207 |
| exageracion | 731 | 56.2% | daxter_0317_jak2_ds112, daxter_0553_jak2_dsek009, daxter_0902_jak3_dax520, daxter_0055_jak1_sksp0052, daxter_0146_jak1_sksp0146 |
| comentarios_secundarios | 206 | 15.8% | daxter_0055_jak1_sksp0052, daxter_0146_jak1_sksp0146, daxter_0477_jak2_ds353, daxter_0400_jak2_ds226, daxter_1190_jakx_dax174r |

## Distribución contextual

Emociones más frecuentes: emocionado=293, determinado=232, asustado=200, picaro=149, neutral=121, confiado=75, sorprendido=58, enfadado=52.

Intenciones más frecuentes: orden=305, aviso=212, exclamacion=160, afirmacion=134, explicacion=134, celebracion=118, queja=70, pregunta=57.

## Longitud

Media 6.45 palabras; mediana 5.0; percentil 90 11. El adaptador debe favorecer intervenciones cortas.

## Límite operativo

La primera versión es un adaptador reversible y offline. Conserva literalmente el contenido base de Atlas, reduce personalidad según riesgo y no entrena ningún LLM.
