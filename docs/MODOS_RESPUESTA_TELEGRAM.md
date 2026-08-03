# Modos de respuesta de Telegram

## Modos

- `automatic`: texto ante texto; audio ante audio cuando TTS y STT estén disponibles.
- `text_only`: siempre texto.
- `audio_only`: siempre audio cuando TTS esté disponible; texto como respaldo técnico.

## Persistencia

La preferencia se guarda por usuario de Atlas dentro de la sección
`response_modes` del estado de Telegram.

## Órdenes conversacionales

Activar texto:

```text
Respóndeme solo por texto.
Contéstame únicamente por texto.
No me respondas con audio.
```

Activar audio:

```text
Respóndeme solo por audio.
Contéstame únicamente por audio.
A partir de ahora responde siempre con audio.
```

Restaurar automático:

```text
Deja de responder solo por texto.
Deja de responder solo por audio.
Cancela el modo solo audio.
Vuelve al modo automático.
```

## Estado de esta entrega

Esta rama implementa la preferencia, la interpretación y la decisión de
enrutado. El envío real con `sendVoice` y la transcripción STT se integrarán
en bloques posteriores. Hasta entonces, los mensajes de voz sin transcripción
mantienen el comportamiento seguro actual.
