# Política de seguridad de invitados

Un interlocutor temporal nunca puede suplantar un perfil permanente ni heredar permisos del titular del bot.

Acciones bloqueadas:
- Home Assistant y dispositivos.
- Lectura o escritura de memoria.
- Archivos y Drive.
- Recordatorios.
- Administración de Atlas.
- Gestión de usuarios y Telegram.
- Copias de seguridad.

El perfil temporal es aislado por conversación y se restaura al titular al cerrarse.
