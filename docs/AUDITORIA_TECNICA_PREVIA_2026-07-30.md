# Auditoría técnica previa de Atlas Core

Fecha: 30 de julio de 2026  
Estado: informe previo a cualquier saneamiento o corrección  
Alcance: `04 - Python/atlas_core`, documentación local y documentación oficial de Google Drive

## Actualización de continuidad — 31 de julio de 2026

Estado del bloque: **parcialmente completado**. El bloqueo de colección causado
por `ai.models` está reparado y la integración controlada del bootstrap de
monitorización es satisfactoria. La suite completa sigue mostrando defectos
preexistentes fuera del alcance de esta intervención y, por tanto, la auditoría
integral todavía no puede declararse cerrada.

### Repositorio y rama oficiales

- Repositorio de desarrollo: `C:\Proyectos\Atlas\atlas_core`.
- Remoto: `https://github.com/REDACTED_b4f38f5848fd/atlas-core.git`.
- Rama principal de GitHub: `main`.
- Rama de esta intervención: `auditoria-limpieza-2026-07-31`.
- Google Drive se reserva para documentación oficial y copias de seguridad; su
  carpeta sincronizada no debe utilizarse como repositorio Git activo.

### Causa raíz de `ai.models` y evidencia

`ModelRegistry` y sus importaciones aparecieron en el commit `abd96e5`. El
historial, todos los objetos Git y las ramas disponibles no contienen ningún
archivo bajo `ai/models/`, aunque `ai/README.md` documenta ese paquete como el
registro y selector de modelos. La causa es la regla histórica `models/` de
`.gitignore`, introducida en `e173ce1`: `git check-ignore` demuestra que también
ignoraba `ai/models/model_registry.py`, no solo el directorio raíz destinado a
modelos descargados.

Los consumidores vigentes son `core/atlas.py`, `main.py` y
`scripts/run_telegram_bot.py`. Esperan construcción sin argumentos y
`get_default_model_name()`. El propio `main.py` documenta `qwen2.5:7b` como
predeterminado; `config.py` declara Ollama como proveedor y permite configurar
`AI_MODEL`.

### Contrato final de modelos

- `ModelDefinition` inmutable con nombre y proveedor.
- `ModelRegistry()` registra `qwen2.5:7b` para Ollama.
- La configuración central puede seleccionar otro modelo predeterminado.
- Registro, resolución, selección y listado explícitos.
- Modelos desconocidos y duplicados producen errores claros.
- El registro no consulta Ollama ni instala modelos; la disponibilidad real
  continúa siendo responsabilidad de `OllamaProvider`.
- `.gitignore` limita `/models/` al directorio raíz y permite versionar
  `ai/models/`.

Archivos de implementación y prueba añadidos o ajustados:

- `.gitignore`;
- `ai/models/__init__.py`;
- `ai/models/model_registry.py`;
- `tests/test_model_registry.py`.

### Integración controlada del bootstrap

`monitoring/bootstrap.py` admite ahora sondas y un monitor Raspberry opcionales
inyectados. Sin inyección mantiene el comportamiento de producción: requiere
host, construye `RaspberryMonitor` y registra su sonda. La prueba
`tests/test_monitoring_bootstrap_integration.py` usa únicamente `tmp_path`, un
emisor Telegram simulado, sondas ficticias, variables temporales e intervalo
acotado.

La prueba demuestra construcción mediante el bootstrap, arranque en hilo,
sonda saludable, excepción aislada en otra sonda, incidencia y notificación,
escritura temporal, recuperación, resolución, segunda notificación, cierre y
ausencia del hilo al terminar. El valor sensible simulado no aparece en los
archivos persistidos.

### Resultados de validación

- `tests/test_model_registry.py`: 5 superados en 0,19 s.
- Tests de supervisor, modelo compartido e integración del bootstrap: 8
  superados en 0,15 s.
- `python -m pytest --collect-only -q`: 856 tests recopilados en 0,44 s, sin
  errores. La salida completa está en
  `docs/auditoria/pytest_collect_final_2026-07-31.txt`.
- `python -m pytest -q`: 848 superados, 263 fallos contabilizados y 2.579
  subtests superados en 158,99 s; 0 omitidos indicados por pytest.

Los fallos globales restantes no importan `ModelRegistry` ni afectan a los
tests de monitorización. Se agrupan en perfiles efectivos y biografías, ayuda y
permisos, interpretación meteorológica, saludo determinista e integridad de
extremos de relaciones. La suite también modifica el contador y la última fecha
de encuentro de REDACTED_2c7b6821719d en `identity/data/people.json`; ese efecto se restauró al
estado exacto de `HEAD` y debe corregirse en una fase posterior mediante mejor
aislamiento de datos de prueba.

### Smoke test predeterminado

No se ejecutó. El ciclo predeterminado abre TCP/SSH contra la Raspberry y usa
`StrictHostKeyChecking=accept-new`, que puede modificar `known_hosts`, además de
ejecutar un script remoto de diagnóstico. Aunque las operaciones remotas son de
lectura y los timeouts son finitos, no se puede garantizar ausencia total de
cambios externos. La prueba de integración controlada cubre el comportamiento
funcional sin asumir ese riesgo.

### Pendientes reales

La reparación de `ModelRegistry` y la validación controlada de monitorización
están completadas. La auditoría integral continúa bloqueada por los fallos
globales enumerados. Deben investigarse como bloques independientes, empezando
por la contaminación de datos persistentes durante pytest y la integridad de
relaciones, antes de declarar limpia la suite.

## Actualización: reparación aislada de monitorización

Repositorio de trabajo: `C:\Proyectos\Atlas\atlas_core`
Estado del bloque: reparación aplicada y pruebas focalizadas superadas; la
validación global queda detenida por un nuevo error de colección ajeno a
monitorización.

### Causa confirmada

`monitoring/supervisor.py` conservaba el supervisor antiguo basado en
`ServiceHealth`, mientras `monitoring/bootstrap.py` y los tests utilizaban el
contrato moderno con `SupervisorProbe`, `HealthCheckResult`, `IncidentManager`,
`NotificationRouter` y `DesktopStateWriter`. Ambos diseños entraron juntos en el
mismo checkpoint Git, por lo que no existía una versión histórica coherente que
restaurar.

### Reparación aplicada

- Un único `AtlasSupervisor` moderno con sondas inyectables.
- Sondas predeterminadas para el consumidor real `monitoring/run_supervisor.py`.
- Eliminación de `ServiceHealth`, sin consumidores reales de ejecución.
- Aislamiento de excepciones por sonda y continuación del resto del ciclo.
- Conversión de fallos en `HealthCheckResult` saneados.
- Integración de incidencias, notificaciones y estado de escritorio.
- Timeouts finitos para HTTP, SSH y configuración temporal.
- Espera interrumpible y cierre limpio.
- Migración del test legado de serialización al modelo compartido.

### Validación ejecutada

- `python -m pytest tests/test_monitoring_supervisor.py -vv`: 5 tests superados.
- `python -m pytest --collect-only -q`: 829 tests recopilados y 8 errores de
  colección ajenos a monitorización.
- `python -m pytest -q`: no ejecutado, porque la instrucción de auditoría obliga
  a detenerse ante un nuevo bloqueo de colección.

### Siguiente bloqueo

Ocho tests de integración fallan al importar `core.atlas` porque no existe el
paquete `ai.models`, aunque `core/atlas.py`, `main.py`,
`scripts/run_telegram_bot.py` y la copia histórica del núcleo importan
`ai.models.model_registry.ModelRegistry`. La carpeta tampoco aparece en las
ramas y commits comprobados. Este defecto debe analizarse como el siguiente
bloque independiente antes de reanudar la suite completa o la limpieza general.

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
