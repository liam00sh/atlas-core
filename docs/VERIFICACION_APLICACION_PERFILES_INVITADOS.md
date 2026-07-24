# Verificación de aplicación — perfiles temporales de invitado

## Confirmado en Drive

- `core/guest_session.py` existe.
- `core/atlas.py` integra `GuestSessionManager`, el filtro de seguridad y el cierre de sesión.
- `core/atlas_social.py` contiene el flujo de saludo, desambiguación y confirmación.
- `core/atlas_users.py` distingue cuenta del bot e interlocutor invitado.
- `console/command_help.py` contiene ayuda para perfiles temporales.
- Los archivos de identidad relacionados fueron actualizados.

## Riesgos pendientes de prueba manual

- Resolución exacta de parentescos con los datos reales de familia.
- Desambiguación de homónimos vivos/fallecidos.
- Cierre del invitado con «adiós» y «salir» desde Telegram.
- Restauración del modo y asistente del titular.
- Bloqueo efectivo de Home Assistant y memoria desde Telegram.

## Casos de prueba recomendados

1. `Estoy con mi padre, salúdalo`.
2. `Estoy con José, salúdalo`.
3. Confirmar un perfil temporal.
4. Intentar `enciende la luz virtual`.
5. Preguntar `qué modos tienes`.
6. Cambiar a modo divertido.
7. Decir `adiós`.
8. Confirmar que el bot vuelve al titular.
