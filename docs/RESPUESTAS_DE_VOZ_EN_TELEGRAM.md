# Respuestas de voz en Telegram

Atlas puede enviar notas de voz reales cuando el modo de respuesta lo requiere.

## Flujo

1. Atlas genera la respuesta textual.
2. `VoiceService` sintetiza la voz configurada.
3. Kokoro produce WAV.
4. FFmpeg convierte WAV a OGG/Opus.
5. Telegram recibe el archivo mediante `sendVoice`.

## Modos

- `automatic`: texto ante texto; audio ante audio cuando el flujo esté disponible.
- `text_only`: siempre texto.
- `audio_only`: audio ante cualquier entrada cuando el flujo esté disponible.

## Respaldo

Si fallan TTS, FFmpeg o Telegram:

- se envía el texto;
- no se borra la preferencia;
- la conversación continúa.

## Limitación actual

La recepción de notas de voz todavía no incluye STT.
