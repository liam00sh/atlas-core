# Monitorización y recuperación controlada

## Estado uniforme

`HealthCheckResult` representa cada observación con identificador, estado,
mensaje, instante, datos adicionales, gravedad opcional, recuperabilidad y
necesidad de intervención. El estado normalizado distingue `healthy`,
`degraded`, `unavailable`, `unknown` y `recovered` sin romper los nombres
históricos del enum.

El supervisor cubre PC, disco local, procesos de Atlas y Telegram, Home
Assistant, Ollama y Raspberry. Una única observación de Raspberry deriva
resultados uniformes para Docker y temperatura; no repite SSH.

## Separación de responsabilidades

- Observar: `SupervisorProbe` y `AtlasSupervisor.collect` no modifican servicios.
- Avisar: `IncidentManager` abre, actualiza, deduplica y resuelve incidencias.
- Recomendar: `RecoveryCoordinator.recommend` devuelve una propuesta sin
  ejecutar el handler.
- Actuar: `RecoveryCoordinator.execute` exige política explícita, confirmación y
  propietario cuando la acción es `owner_only`; registra solicitante, resultado
  y error.

No hay recuperación automática activada. Los handlers se inyectan y las pruebas
usan funciones falsas sin infraestructura.

## Persistencia y panel

`HealthHistoryStore` escribe de forma atómica, tolera JSON corrupto y rota por
número máximo de entradas. El supervisor usa una ruta junto a las incidencias;
en pytest esa ruta procede de `tmp_path`.

El estado del panel contiene heartbeat, todas las comprobaciones, incidencias
abiertas, recomendaciones y recuperaciones recientes. El widget muestra el
resumen sin ser una dependencia del supervisor.

## Estado funcional

- Implementado: observación, aislamiento de excepciones, incidencias,
  deduplicación, recuperación/cierre, historial y panel.
- Validado focalmente: estados, excepción aislada, deduplicación, cierre,
  recomendación sin ejecución, autorización y denegación.
- Preparado: coordinador de recuperación con handlers inyectados.
- Pendiente: registrar políticas y handlers reales de producción y conectar una
  orden conversacional explícita; hasta entonces la ayuda no lo anuncia como
  ejecutable.
