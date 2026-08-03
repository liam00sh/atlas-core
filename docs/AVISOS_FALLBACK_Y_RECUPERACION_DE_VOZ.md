# Avisos de fallback y recuperación de voz

Atlas distingue una voz alternativa elegida voluntariamente de una voz usada por fallo.

Los avisos se emiten una sola vez por transición y se guardan en:

- `data/voice/status.json`
- `data/voice/events.jsonl`

Estados contemplados:

- inicio de fallback;
- recuperación de la voz configurada;
- ausencia total de voz.

La integración con Telegram consumirá los eventos estructurados sin acoplar el bot al subsistema de voz.
