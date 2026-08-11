# Cierre de fase — Home Assistant y automatizaciones domésticas

Estado: concluida y validada.

## REDACTED_0f38c2ded26fnes cerradas

- Control de la luz del acuario pequeño.
- Control del oxígeno del acuario pequeño.
- Control conjunto del acuario pequeño.
- Control de la luz del acuario grande.
- Programación horaria persistente mediante Home Assistant.
- Activación y desactivación de horarios.
- Temporizadores de encendido con apagado automático.
- Compatibilidad por consola local y Telegram.
- Mensajes de estado coherentes y tratamiento del falso HTTP 404.
- Validación de permisos y entidades autorizadas.

## Siguiente trabajo

Antes de continuar con nuevas funciones domésticas se integrarán los usuarios amigos y se corregirán pequeños problemas de comunicación.

## Mejora de IA previa a continuar la Fase 6

- Roles locales `fast`, `reasoning` y `deep`; `external` deshabilitado.
- Router explicable, override manual, validación y fallback ascendente.
- Estado conversacional compartido por CLI, Telegram y futura voz.
- Separación estructural de identidad, domicilio, ubicación y presencia.
- Jerarquía explícita de fuentes y contrato decisión/redacción.
- Mensajes contextuales, deduplicación de eventos y espera tras 4,5 s reales.
- Benchmark y regresiones de Vega en `tests/ai_benchmark/`.
- La Fase 6 de voz sigue abierta y el laboratorio Daxter no se modifica.
