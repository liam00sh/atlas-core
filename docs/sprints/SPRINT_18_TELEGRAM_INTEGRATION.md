# Sprint 18 — Integración segura de Telegram

## Resultado

Telegram se incorpora como una interfaz opcional de **Atlas** mediante long
polling. El canal no contiene una inteligencia paralela: traduce cada mensaje
a un `TelegramRequestContext` y lo entrega a `Atlas.process()`. Drive, memoria,
relaciones, IA, confirmaciones y herramientas continúan perteneciendo al
núcleo.

`main.py` no participa en el servicio. La CLI arranca con normalidad aunque no
exista configuración Telegram.

## Dependencias y transporte

La implementación utiliza `urllib.request` de la biblioteca estándar. La Bot
API necesaria para esta primera versión solo requiere `getUpdates`,
`sendMessage`, `getMe` y `getWebhookInfo`; no se añadió una dependencia externa
cuya compatibilidad con Python 3.14 pudiera variar. `TelegramBotClient` queda
detrás de un protocolo, por lo que podrá sustituirse sin alterar gateway,
sesiones ni núcleo.

No se implementan webhooks. Si `getWebhookInfo` declara una URL, el servicio se
detiene con un mensaje seguro y nunca elimina el webhook silenciosamente.

## Flujo

```text
getUpdates
  -> validación de DTO y chat privado
  -> deduplicación y offset persistente
  -> rate limit por telegram_user_id + chat_id
  -> TelegramIdentityLinker
  -> TelegramSessionManager
  -> política de permisos del canal
  -> AtlasCoreAdapter
  -> Atlas.process()
  -> fragmentación
  -> sendMessage
```

`AtlasCoreAdapter` serializa el núcleo actual porque Atlas conserva estado
mutable del usuario activo. Antes de procesar selecciona el usuario vinculado,
establece la sesión y el contexto del canal; después restaura el usuario, la
sesión y el contexto anteriores incluso si hay una excepción. Dos sesiones no
pueden alterar el núcleo fuera de orden. El diseño permite concurrencia en las
capas HTTP y de gateway, pero el núcleo compartido se protege de forma
conservadora.

El adaptador mantiene por sesión el contexto reciente de IA, confirmaciones y
estado heredado de privacidad de memoria. Esos estados no se mezclan con la CLI
ni con otro chat. Las propuestas del Sprint 13 y la navegación Drive ya usan el
`session_id` persistente del núcleo. Una petición Telegram tampoco puede cambiar
al usuario autenticado mediante frases como «soy otra persona» ni volver al
usuario principal si eso alteraría su identidad vinculada.

## Identidad y vinculación

La clave estable es exclusivamente `telegram_user_id`. `username`, nombre y
apellido son metadatos opcionales y nunca resuelven un usuario Atlas. `chat_id`
forma parte de la sesión y de la propuesta de vinculación, pero no sustituye la
identidad Telegram.

Estados:

- `unlinked`
- `link_pending`
- `linked`
- `blocked`
- `revoked`

`/start` crea un código criptográficamente aleatorio de diez caracteres. Solo
se persisten un prefijo público de tres caracteres, una sal aleatoria y un
derivado PBKDF2-HMAC-SHA256 de 120.000 iteraciones. El código completo nunca se
guarda. Caduca a los 600 segundos por defecto, es de un solo uso y admite cinco
intentos dirigidos por su prefijo antes de bloquear la propuesta y la cuenta.
Un nuevo `/start` cancela la propuesta anterior.

La capacidad local `telegram.link.confirm` requiere:

- usuario Atlas real;
- permiso `telegram.admin_link`;
- `confirmed=True`;
- código pendiente, vigente y no usado.

`telegram.admin.revoke` aplica el mismo patrón con
`telegram.admin_revoke`. Los permisos administrativos solo se conceden por el
adaptador local a perfiles con rol `owner` o `admin`, y quedan fuera de la
política del canal Telegram.

## Personalidades

`/daxter` y `/coco` llaman a `IdentityManager.change_identity()` con
persistencia. No existe una preferencia Telegram independiente. Una elección
hecha desde Telegram se observa en la CLI y viceversa. El adaptador restaura al
usuario anterior después de cada operación, por lo que Liam y Saray mantienen
preferencias separadas.

La sesión ya admite atributos temporales aislados por `telegram_user_id` y
`chat_id`. La presentación y autorización explícita de invitados se deja para
un sprint posterior: una cuenta no vinculada no puede seleccionar personalidad
ni heredar identidad, permisos o datos del anfitrión.

## Permisos

El permiso efectivo es la intersección de los permisos centrales del usuario y
la lista permitida por Telegram. El contexto autoritativo del canal sustituye
cualquier `channel="cli"` heredado durante la petición y evita que metadatos de
una herramienta falsifiquen usuario, chat, mensaje o sesión.

Política inicial del canal:

- lecturas ya autorizadas de sistema, filesystem, Drive, conocimiento y memoria;
- flujo controlado de propuesta, confirmación, actualización y borrado de memoria;
- nunca `memory.sensitive.read` ni `memory.sensitive.write` implícitos;
- nunca administración de vinculaciones desde Telegram.

Telegram no concede permisos nuevos de Drive, memoria o relaciones y no evita
confirmaciones existentes.

## Comandos

Públicos: `/start`, `/help`, `/status`, `/whoami`, `/cancel`.

Vinculados: `/assistant`, `/daxter`, `/coco`, `/unlink` y
`/unlink_confirm`. `/unlink` solo crea un estado pendiente. La confirmación
elimina la asociación y las sesiones del canal; no elimina el usuario Atlas,
su memoria ni su personalidad persistente.

Solo se admiten chats privados. Grupos, canales, inline mode, audio, imágenes,
documentos y webhooks están fuera del Sprint 18.

## Persistencia y secretos

Ruta predeterminada: `data/integrations/telegram/`.

- `state.json`: asociaciones, propuestas derivadas, sesiones mínimas y offset;
- `audit.jsonl`: eventos minimizados;
- `polling.lock`: bloqueo de instancia única.

Las escrituras JSON son UTF-8, atómicas mediante archivo temporal y
`os.replace`. Un lock de archivo coordina procesos locales y cada instancia
recarga cambios externos antes de leer o escribir, lo que permite confirmar un
código desde otra sesión local sin reiniciar el bot. JSON ausente o corrupto
produce un estado vacío seguro. La ruta está excluida de Git.

El token solo se obtiene de `ATLAS_TELEGRAM_BOT_TOKEN`. No se serializa, no se
registra y los errores HTTP nunca incluyen URL, petición ni token. La auditoría
anonimiza los IDs con SHA-256 truncado y no guarda mensajes, respuestas,
códigos, documentos, memoria o prompts. La opción de contenido de depuración
existe en configuración, está desactivada por defecto y esta versión no la usa
para registrar contenido.

## Polling y recuperación

- offset persistente después de cada update procesado;
- updates antiguos o repetidos ignorados;
- timeout configurable;
- backoff exponencial limitado a 60 segundos con jitter;
- parada mediante evento y señales `SIGINT`/`SIGTERM`;
- bloqueo local exclusivo con PID;
- recuperación automática de un lock cuyo PID ya no existe;
- fallback de Markdown a texto plano;
- respuestas divididas por debajo del límite de Telegram;
- bloques de código cerrados y reabiertos cuando cruzan fragmentos.
- enfriamiento temporal de 15 segundos después de tres errores consecutivos
  del núcleo en la misma sesión;

El offset se confirma después de ejecutar el núcleo y antes de enviar la
respuesta. `sendMessage` reintenta tres veces los errores temporales. Si todos
los intentos fallan, la respuesta puede perderse, pero el update no vuelve a
ejecutar una acción sensible después de reiniciar.

Un bloqueo corrupto no se elimina automáticamente. Debe comprobarse que no hay
otro proceso y retirar manualmente `data/integrations/telegram/polling.lock`.

## Ejecución

```powershell
python scripts/check_telegram_config.py --offline
python scripts/check_telegram_config.py --live
python scripts/run_telegram_bot.py
```

La comprobación `--live` es manual y nunca forma parte de pytest.

## Límites conocidos

- No se realizó una conexión real porque el token no se proporciona a Codex.
- El núcleo actual es mutable y se serializa; la concurrencia real entre
  usuarios requerirá en el futuro contextos de Atlas completamente aislados.
- No existe todavía flujo de invitado presentado por un anfitrión.
- No hay cancelación forzosa segura de una tarea Python del núcleo que exceda el
  timeout; se ignora su respuesta tardía y el adaptador restaura el contexto.
- Los contextos de IA y confirmaciones del canal sobreviven mientras vive el
  proceso, pero no se serializan porque pueden contener conversación sensible.
- No se implementan mensajes que no sean texto ni chats no privados.

## Validación automática

La suite Telegram contiene 78 pruebas offline. Cubre configuración, redacción
de secretos, cliente HTTP, persistencia entre instancias, códigos, caducidad,
intentos, suplantación por username, comandos, permisos, personalidades,
sesiones, cambio de usuario bloqueado, contextos de IA, confirmaciones,
fragmentación, Markdown, rate limit, cooldown, concurrencia, offsets, reinicio,
webhook, backoff, reintento de respuestas, bloqueo de instancia y herramienta
administrativa. No abre conexiones reales.
