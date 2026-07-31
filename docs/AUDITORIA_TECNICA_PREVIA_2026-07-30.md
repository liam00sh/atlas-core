# Auditoría técnica previa de Atlas Core

Fecha: 30 de julio de 2026  
Estado: informe previo a cualquier saneamiento o corrección  
Alcance: `04 - Python/atlas_core`, documentación local y documentación oficial de Google Drive

## 1. Condiciones de partida

El árbol de trabajo ya contenía numerosos cambios sin confirmar y archivos nuevos
antes de iniciar esta auditoría. Esos cambios se consideran trabajo preexistente y
no deben revertirse, mezclarse ni atribuirse a la auditoría.

La suite completa no alcanza la ejecución de tests. La colección se detiene con:

`ImportError: cannot import name 'SupervisorProbe' from 'monitoring.supervisor'`

El test `tests/test_monitoring_supervisor.py` espera la API nueva
`AtlasSupervisor(probes=..., incident_manager=..., notification_router=...,
state_writer=..., interval_seconds=...)`, mientras que
`monitoring/supervisor.py` conserva un constructor sin parámetros y un modelo
anterior basado en `ServiceHealth`. Esta incompatibilidad debe corregirse antes
de considerar válida cualquier cifra global de tests.

## 2. Arquitectura observada

Atlas sigue una arquitectura de fachada con `core.atlas.Atlas` y mixins por área.
La separación conceptual es adecuada:

- `core`: orquestación y prioridades;
- `assistant_identity`: identidades, modos y bancos de frases;
- `identity`: personas, animales y relaciones;
- `memory` y `knowledge`: memoria operativa y recuperación;
- `automation`: automatizaciones y Home Assistant;
- `telegram_interface`: transporte de Telegram;
- `monitoring`: salud, incidencias y supervisión;
- `tools`: capacidades ejecutables.

La estructura real ha crecido bastante más que la arquitectura documentada de
Fase 3. El manual técnico oficial todavía describe principalmente
`atlas.py`, `atlas_ai.py`, `atlas_users.py` y `atlas_commands.py`, aunque el
núcleo actual incorpora más mixins y servicios. La documentación oficial indica
que los cambios funcionales deben reflejarse también en Changelog, Decisiones
Técnicas y el documento de fase.

## 3. Hallazgos y propuestas

### P0. Suite bloqueada durante colección

Evidencia:

- `tests/test_monitoring_supervisor.py` importa `SupervisorProbe`;
- `monitoring/supervisor.py` no define esa clase;
- el constructor esperado por el test no coincide con el implementado.

Propuesta: consolidar el supervisor sobre los modelos compartidos de
`monitoring.models`, `IncidentManager`, `NotificationRouter` y
`DesktopStateWriter`, manteniendo compatibilidad con el lanzador existente.
Después, ejecutar primero los tests de monitorización y luego toda la suite.

### P1. Copia de producción dentro de `core`

`core/atlas_backup_before_stage_e.py` no presenta referencias detectadas y
duplica una versión anterior del núcleo. Su ubicación dentro del paquete de
producción aumenta el ruido de búsquedas, análisis estático y mantenimiento.

Propuesta: no eliminarla todavía. Verificar historial Git, contenido diferencial,
imports dinámicos y documentación. Si es una copia de seguridad manual sin uso,
trasladar su valor histórico a Git o a `11 - Backups` y eliminarla del paquete
solo después de una suite limpia.

### P1. Personalidad de Daxter distribuida y parcialmente duplicada

Existen reglas y frases de Daxter en:

- `assistant_identity/identities/daxter.py`;
- `assistant_identity/phrases/daxter_phrases.py`;
- `conversation/personality.py`;
- `conversation/personality_profile.py`;
- `conversation/original_phrases.py`;
- `conversation/game_references.py`;
- rutas deterministas de `core` y Telegram.

Los identificadores internos en minúsculas (`"daxter"`) son correctos como
claves normalizadas. La presentación al usuario debe usar siempre el
`display_name` canónico. `conversation/personality_profile.py` no mostró
consumidores en la búsqueda inicial y es candidato a legado, pero no se propone
eliminarlo hasta verificar imports dinámicos y cobertura.

Propuesta: una única fuente canónica de identidad y `display_name`, manteniendo
los bancos de frases como datos. Eliminar reglas duplicadas solo mediante tests
de regresión para Daxter y Coco.

### P1. Dos dominios de relaciones

El grafo familiar usa `identity.relationship` y
`identity.relationship_engine`. El sistema de amigos usa además
`core.atlas_friends.FriendsRepository` con su propio almacenamiento, niveles,
hechos y permisos. Esta separación permite funciones específicas, pero crea
riesgo de identidades duplicadas, alias divergentes y respuestas distintas entre
familiares y amigos.

Propuesta: conservar ambos sistemas durante esta auditoría; documentar el límite
de responsabilidad y añadir pruebas de identidad cruzada, alias, persistencia,
conflictos y consultas equivalentes. Una unificación de almacenamiento sería un
cambio arquitectónico, no una limpieza segura.

### P1. Documentación desfasada respecto al árbol actual

La documentación oficial de Fase 3 reconoce una arquitectura por mixins y remite
al documento 27 para el desarrollo posterior. Sin embargo, el árbol actual
incluye automatización, Home Assistant, Telegram, monitorización, launchers,
conocimiento semántico y vida diaria que no aparecen completos en el árbol del
manual técnico.

Propuesta: después de estabilizar el código, actualizar como mínimo el índice
maestro, el manual técnico, el Changelog, las decisiones técnicas y los manuales
especializados. No modificar documentación oficial para declarar estable una
implementación mientras la suite siga bloqueada.

### P1. Artefactos temporales y resultados históricos

Candidatos visibles:

- `pytest_temp/`;
- `pytest_temp_stage_c/`;
- `pytest_temp_stage_c_real/`;
- `.pytest_cache/`;
- `.pytest_runtime/`;
- `pytest_resultado.txt`;
- `errores_pytest.txt`;
- `resultado_tests_completo.txt`;
- `resultado_tests_detallado.txt`;
- `test_results_full.log`;
- `aplicar_correcciones.py`;
- scripts `validar_*`.

Algunos están ignorados y otros pueden ser evidencia histórica o herramientas
manuales. No se autoriza su eliminación solo por el nombre.

Propuesta: para cada candidato, comprobar seguimiento Git, referencias,
contenido, fecha, equivalencia con scripts actuales y necesidad documental.
Eliminar únicamente cachés regenerables y archivos sin referencias después de
la validación completa.

### P1. Dependencias y configuración

`requirements.txt` contiene dependencias de ejecución y `pytest`, mientras
`requirements-google-drive.txt` separa la integración de Drive. La presencia de
pytest como dependencia principal mezcla runtime y desarrollo.

Propuesta: no cambiar dependencias durante la corrección inicial. Más adelante,
separar dependencias de runtime, desarrollo/tests e integraciones opcionales,
verificando imports reales y los entornos de PC/Raspberry.

### P1. Riesgos de red, procesos y bloqueo

Existen llamadas HTTP, TCP, SSH y subprocesos en monitorización, automatización,
Telegram, información del sistema e integraciones. Varias tienen timeout, pero
deben revisarse sistemáticamente para asegurar:

- timeout finito;
- ausencia de `shell=True`;
- argumentos no construidos desde entrada sin validar;
- degradación segura;
- no bloquear `Atlas.process()`;
- redacción de secretos en logs y auditorías.

La comprobación inicial no encontró `.env` seguido por Git ni secretos literales
obvios en el código examinado.

### P2. Tamaño y responsabilidades del núcleo

`core/atlas.py` continúa siendo la fachada correcta, pero la expansión por mixins
ha generado numerosos puntos de prioridad. El riesgo principal ya no es solo el
tamaño de un archivo, sino el orden implícito de resolución entre comandos,
familia, amigos, autoconocimiento, memoria, automatización, conversación e IA.

Propuesta: documentar y probar una tabla única de precedencias. No dividir más
módulos hasta demostrar responsabilidades mezcladas concretas, ya que una
fragmentación adicional podría empeorar la trazabilidad.

### P2. Rendimiento

Áreas a medir antes de optimizar:

- inicialización de Atlas y carga repetida de JSON;
- inicializador familiar idempotente;
- construcción de prompts y recuperación de relaciones;
- búsquedas de personas/amigos sin índices;
- escrituras de auditoría por turno;
- sondeos HTTP/SSH/TCP en el supervisor;
- importación de módulos opcionales al arrancar.

Propuesta: usar benchmarks reproducibles y contadores de I/O. No introducir
cachés sin política de invalidación, especialmente para identidades, permisos,
presencia doméstica y memoria.

## 4. Plan de saneamiento controlado

1. Corregir la incompatibilidad del supervisor sin cambiar comportamiento ajeno.
2. Ejecutar tests de monitorización.
3. Ejecutar la suite completa y clasificar fallos preexistentes.
4. Añadir regresiones dirigidas para Daxter, relaciones, amigos, permisos,
   Telegram, Home Assistant, memoria y contexto.
5. Corregir únicamente defectos reproducidos.
6. Verificar candidatos obsoletos con búsquedas estáticas, imports dinámicos,
   historial Git y suite completa.
7. Eliminar solo elementos regenerables o completamente no referenciados.
8. Medir rendimiento antes y después de cada optimización.
9. Actualizar documentación una vez que código y tests sean coherentes.

## 5. Elementos que no deben eliminarse aún

- `core/atlas_backup_before_stage_e.py`;
- módulos históricos de personalidad;
- repositorio específico de amigos;
- scripts de corrección o validación;
- resultados históricos de pruebas;
- carpetas temporales cuyo proceso propietario no se haya identificado.

Ninguno cuenta todavía con la demostración completa exigida para una eliminación
segura.
