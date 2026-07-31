# Menú de ayuda por permisos efectivos

## Reglas

### Telegram
- Usuario en su propio bot: permisos de su perfil.
- REDACTED_2c7b6821719d en su propio bot: administrador y ayuda completa.
- Cualquier usuario desde el bot de otra persona: invitado temporal.
- Un administrador desde un bot ajeno no conserva permisos administrativos.
- Solo se muestran capacidades cuyo canal incluye Telegram.
- `/help` delega en el mismo núcleo contextual que `ayuda`; no mantiene una
  lista privada paralela.

### PC
- REDACTED_2c7b6821719d: administrador.
- REDACTED_bc04a68d9192, REDACTED_aebac53c46bb y REDACTED_0392c3d1b4d3: permisos de sus perfiles.
- Persona sin perfil conocido: invitado.

## Principio

La ayuda se filtra por los permisos efectivos de la sesión, no por el nombre reconocido.

La visibilidad se calcula antes de la búsqueda exacta, por alias, aproximada o
por intención. Una búsqueda no puede recuperar una entrada previamente oculta.
Las acciones domésticas que requieren presencia solo aparecen con
`home_verified`; presencia ausente o desconocida aplica la política segura.

En el estado actual:

- REDACTED_2c7b6821719d propietario ve las capacidades `owner_only`.
- Un administrador que no sea propietario no ve `owner_only`.
- REDACTED_aebac53c46bb no ve `crear perfil de usuario` sin `user_management`.
- REDACTED_bc04a68d9192 solo ve controles domésticos cuando el motor efectivo le concede
  `home.control.*` y consta presencia doméstica verificada.
- Un invitado o una sesión sin perfil solo ve capacidades públicas.

Las consultas `cómo hago para`, `quiero saber cómo` y `qué comando uso`
explican. Las formas imperativas continúan hacia el flujo de ejecución. Si la
capacidad existe pero está oculta, se informa de la falta de disponibilidad;
si no existe, Atlas no inventa un comando.
