# Sprint 18.1 — Servicio residente y mensajería entre usuarios

## Objetivos

- Telegram se inicia en segundo plano al entrar en Windows.
- El proceso no depende de una terminal abierta.
- Un supervisor reinicia el bot si termina y recarga cambios de código.
- Cualquier usuario Atlas vinculado puede enviar mensajes o recordatorios a
  cualquier otro usuario Atlas vinculado al mismo bot.

## Ejemplos

- `Recuérdale a REDACTED_bc04a68d9192 que compre pan.`
- `Dile a REDACTED_2c7b6821719d que ya he llegado.`
- `Recuerda a REDACTED_bc04a68d9192 a las 17 que vaya al mercado.`
- `Recuérdale a REDACTED_d296a64095dd mañana a las 8:30 que lleve la mochila.`

Las asociaciones se resuelven mediante `atlas_user_id` y `telegram_user_id`; no
hay nombres codificados en la implementación.

## Persistencia

La sección `deliveries` de `data/integrations/telegram/state.json` conserva las
entregas pendientes. Si el PC está apagado en el momento programado, se envían
al volver a arrancar Atlas Telegram.

## Seguridad

- Solo pueden enviar usuarios Telegram vinculados o una sesión local Atlas.
- Solo se puede entregar a usuarios Atlas actualmente vinculados al bot.
- El contenido se limita a 1500 caracteres.
- El token no se almacena en la cola ni en los registros.
