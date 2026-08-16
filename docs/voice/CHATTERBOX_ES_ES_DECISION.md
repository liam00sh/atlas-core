# Decisión técnica: español de España en Chatterbox

## Evidencia

- La batería humana B1 no acredita un ganador global ni pronunciación peninsular consistente.
- Chatterbox Multilingual V3 se presenta oficialmente como la generación recomendada frente al legado V2.
- Resemble AI publica un paquete monolingüe específico para España: `ResembleAI/Chatterbox-Multilingual-es-es`.
- La documentación oficial advierte que el idioma de la referencia puede transferir acento y propone `cfg_weight=0` para mitigarlo; esto no equivale a garantizar español de España en B1.

Fuentes primarias:

- https://github.com/resemble-ai/chatterbox
- https://huggingface.co/ResembleAI/Chatterbox-Multilingual-es-es

## Decisión

La comparación humana ciega ya se completó. `es-ES` gana por español de España,
media global, ausencia de artefactos/cortes y número de primeros puestos. V2
queda segundo y conserva una ventaja pequeña de parecido con Daxter. La
configuración compartida de `es-ES` se congela como candidata reproducible; no
se harán sustituciones fonéticas arbitrarias ni una búsqueda indefinida de
parámetros.

Configuraciones comparadas:

1. B1 actual (V2 multilingüe).
2. V3 multilingüe general, si el checkpoint está disponible localmente.
3. V3 monolingüe `es-ES`, si el checkpoint está disponible localmente.

La descarga de modelos queda desactivada por defecto. El laboratorio debe recibir una ruta local explícita y registrar modelo, revisión, SHA256, semilla y configuración.

La selección humana no cierra Fase 6: las palabras con tilde y los cortes
puntuales requieren una regresión dirigida, y todavía falta completar STT
160/160 y el E2E posterior.

## Estrategia para términos ingleses

Cada término se compara sin escritura pseudo-fonética:

- forma original;
- forma original dentro de una frase española corta;
- forma original seguida de una aposición semántica en español.

Términos mínimos: Home Assistant, Docker y Telegram. Opcionales: GitHub, Google Drive, Ollama y Whisper.
