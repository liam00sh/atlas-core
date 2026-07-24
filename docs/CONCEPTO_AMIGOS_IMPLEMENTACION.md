# Concepto «Amigos» — implementación funcional

## Escala social interna
- 0 — Conocido.
- 1 — Amigo conocido.
- 2 — Amigo.
- 3 — Amigo cercano.
- 4 — Mejor amigo.

Todos los amigos son conocidos, pero no todos los conocidos son amigos. Al usuario se le muestra normalmente «amigo» y no el nivel interno.

## Evolución automática
- 85 % o más: Atlas aplica el cambio automáticamente y lo registra.
- Entre 60 % y 84,99 %: Atlas pregunta al usuario.
- Menos del 60 %: mantiene la relación actual.

## Permisos
La amistad no concede permisos automáticamente. Solo amistades de nivel 3 o 4 pueden recibir permisos delegados y siempre mediante una concesión explícita.

Además:
- el concedente debe poseer el permiso;
- el permiso debe ser delegable;
- no puede ser administrativo;
- debe tener un alcance concreto;
- solo será efectivo cuando la ubicación del amigo indique que está en casa.

Fuera de casa, el permiso permanece registrado, pero no es efectivo. El administrador conserva siempre todos los permisos.
