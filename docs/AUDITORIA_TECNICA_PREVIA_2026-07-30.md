# Auditoría técnica previa de Atlas Core

Fecha: 30 de julio de 2026  
Estado: revisión final completada; rama preparada para integración
Alcance: `04 - Python/atlas_core`, documentación local y documentación oficial de Google Drive

## Revisión final de calidad y preparación para integración

Estado del bloque: **completado y validado**. No se añadieron funcionalidades ni
se modificaron APIs estables. Los únicos cambios de código son la eliminación de
imports demostrablemente no usados y la corrección del número de versión
publicado, que estaba desfasado respecto a la versión oficial 0.5.0.

### Artefactos revisados

| Archivo o grupo | Decisión | Evidencia y motivo |
| --- | --- | --- |
| 49 archivos `desktop.ini` | Eliminar | Metadatos binarios de Windows, idénticos entre sí, sin consumidores y ya cubiertos por `.gitignore`. |
| `pytest_temp/`, `pytest_temp_stage_c/`, `pytest_temp_stage_c_real/` | Eliminar | Once salidas persistidas por tests; regenerables y sin consumidores. |
| `pytest_resultado.txt`, `errores_pytest.txt`, `resultado_tests_completo.txt`, `resultado_tests_detallado.txt` | Eliminar | Salidas históricas en UTF-16 con cifras superadas; el resultado vigente queda registrado en esta auditoría. |
| `docs/auditoria/pytest_collect_final_2026-07-31.txt` | Eliminar | Volcado de colección obsoleto de 856 tests; no era referenciado y el resultado vigente es 875. |
| `console/command_manager_patched.py` | Eliminar | Copia byte a byte de `console/command_manager.py`, sin imports. |
| `automation/automation_permissions (1).py` | Eliminar | Copia anterior del módulo activo, sin imports y sin validaciones actuales. |
| `automation/home_intent_service_backup.py` | Eliminar | Copia reducida y anterior del servicio activo, sin consumidores. |
| `conversation/TEMP_intent_refined.py` | Eliminar | Experimento antiguo divergente de `conversation/intent.py`, sin consumidores. |
| `core/atlas_backup_before_stage_e.py` | Eliminar | Copia manual anterior del núcleo, sin imports; su historia permanece recuperable en Git. |
| `utils/text_normalizer_fixed.py` | Eliminar | Copia anterior del normalizador activo, sin consumidores. |
| `tests/__tmp_conftest_pytest_temp_fixed.py` | Eliminar | Fixture histórico no cargado por pytest y sustituido por `tests/conftest.py`. |
| `daily_life/__init__.txt` | Eliminar | Duplicado accidental de `daily_life/__init__.py`. |
| `aplicar_correcciones.py`, `validar_correccion.ps1`, `clean_and_test.ps1` | Eliminar | Scripts puntuales ya aplicados; los dos últimos ejecutaban la batería antigua con `unittest`. |
| `scripts/install_atlas_launcher_task.ps1`, `install_atlas_startup_tasks.ps1`, `status_atlas_launcher.ps1`, `stop_atlas_launcher.ps1` | Eliminar | Flujo legado de una o cuatro tareas, con ruta absoluta a H:. Está sustituido por los dos launchers y scripts portables `*_split_tasks.ps1`. |
| `.pytest_cache/`, `.pytest_runtime/`, `__pycache__/` | Conservar fuera de versión | Cachés locales ignoradas, regenerables y no incluidas en Git. |
| `run_tests_safe.ps1` | Conservar | Herramienta activa y portable para ejecutar pytest con directorio temporal aislado. |
| `automation/backup_adapter.py` | Conservar | Adaptador activo consumido por Stage C, catálogo, integraciones y tests. |
| `ai/cache/response_cache.py` | Conservar | Caché activa importada por `core/atlas.py`. |
| `validar_monitorizacion_raspberry.py` | Conservar y documentar | Diagnóstico manual vigente; puede contactar la Raspberry y por ello no se ejecutó durante esta revisión. |
| `docs/sprints/TEST_RESULTS_*.md`, `CORRECCION_TZDATA_WINDOWS.md` | Conservar | Evidencia histórica fechada, no confundida con el resultado vigente. |

No se trasladaron backups al árbol de producción. Las copias manuales eliminadas
no contenían información única y siguen disponibles en el historial Git; los
backups operativos externos quedan fuera del repositorio y de esta intervención.

### Revisión arquitectónica y código legado

- Se analizaron estáticamente 271 archivos Python de producción y herramientas.
  Tras la limpieza, los únicos imports que el análisis marca como no usados son
  reexportaciones deliberadas en `logger.py` y `core/version.py`.
- Se retiraron 16 imports sin uso en launchers, identidad, ayuda, relaciones,
  monitorización, Telegram y herramientas de Drive. `compileall` finalizó con
  código 0.
- Los comandos sin importador estático se conservan porque
  `console.command_manager` los descubre dinámicamente.
- `monitoring.desktop_widgets` y `monitoring.run_supervisor` se conservan
  como puntos de entrada ejecutados por los launchers.
- `automation/device_agent.py`, `device_policy.py`,
  `device_registry.py`, `pc_access_policy.py` y
  `monitoring/startup_checks.py` no tienen consumidor estático actual, pero
  definen contratos de la arquitectura de automatización y supervisión. No hay
  evidencia suficiente para eliminarlos en una revisión pre-merge.
- `conversation/personalities.py`, `personality_manger.py` y
  `logger.py` son capas de compatibilidad explícitas. Se conservan para no
  romper imports externos o instalaciones anteriores.
- `conversation/personality_profile.py` y `responses.py` son datos
  estructurados/legado documentado sin consumidor actual. Se conservan hasta
  decidir su migración en una intervención funcional con regresiones propias.
- Los dos dominios de relaciones —familia e integración de amigos— siguen
  separados intencionadamente. Unificarlos excedería una limpieza segura.
- `requirements.txt` incorpora `python-dotenv` por un consumidor real y
  mantiene pytest para `run_tests_safe.ps1`; las dependencias opcionales de
  Google Drive continúan separadas en `requirements-google-drive.txt`.

Riesgos no bloqueantes: revisar en una fase futura los contratos de dispositivos
aún no integrados, decidir la retirada formal de las capas de compatibilidad y
separar dependencias de runtime y desarrollo. Ninguno justifica cambios
adicionales antes de integrar esta rama.

### Documentación revisada

- `README.md`: versión 0.5.0, estado de Fase 6, estructura real y comandos
  oficiales de pytest.
- `core/version.py` y los ejemplos de `commands/version.py`: alineados con
  la versión oficial 0.5.0.
- `tests/evidencias/README.md`: referencia al runner vigente
  `run_tests_safe.ps1`.
- Este informe y su equivalente oficial de Google Drive: cierre de limpieza,
  arquitectura, Git, validación y riesgos.
- Changelog y Roadmap oficiales: nota final de auditoría añadida sin reescribir
  su historial.

Se revisaron además el manual técnico, decisiones técnicas, índice maestro,
manual de instalación, manual de pruebas, Telegram, Home Assistant,
automatizaciones y monitorización. Sus secciones históricas conservan su versión
original; los documentos especializados vigentes ya describen 0.5.0, los dos
launchers, permisos, auditoría y ejecución degradada. El manual técnico de Fase
3 sigue siendo deliberadamente histórico y no se renombra como manual global.

### Revisión Git frente a `main`

- La rama parte del mismo `main` remoto y estaba cinco commits por delante
  antes de este cierre; no se realizó merge ni rebase.
- Se revisaron archivos añadidos, eliminados y modificados, cambios grandes,
  extensiones binarias, dependencias y rutas locales.
- El cambio grande de `identity/data/relationships.json` corresponde a la
  eliminación demostrada de relaciones huérfanas. El estado final contiene 44
  personas, 4 animales, 254 relaciones, cero extremos inválidos, cero
  autorrelaciones y cero duplicados exactos.
- No se añadieron binarios. Los únicos binarios del diff de limpieza son
  eliminaciones de `desktop.ini`.
- El escaneo de todo el árbol versionado no encontró claves de AWS, GitHub,
  OpenAI o Google ni bloques de clave privada. `.env.example` mantiene el
  token vacío y `.env` no está versionado.
- No existen secretos, credenciales ni tokens reales añadidos. Los datasets de
  identidad familiar pertenecen al dominio ya versionado y sus cambios son las
  correcciones documentadas de integridad y alias, no inclusiones accidentales.
- No quedan rutas absolutas al repositorio en código o scripts activos. Las
  menciones a C: y H: se limitan a documentación histórica/operativa.

### Validación final

- `python -m pytest --collect-only -q`: **875 tests recopilados** en 0,48 s,
  sin errores.
- `python -m pytest -q`: **875 superados**, **2.324 subtests superados**,
  0 fallos y 0 errores en 169,22 s.
- Los SHA-256 de `people.json`, `animals.json` y `relationships.json`
  fueron idénticos antes y después de la suite.
- El conjunto de `git status --porcelain` fue idéntico antes y después de
  pytest: la suite no creó ni modificó datos reales y no se restauró ningún
  archivo.
- No se contactaron Raspberry, Home Assistant, Telegram, Ollama, dispositivos
  domésticos ni otros servicios externos durante la validación.

Conclusión: **la rama está lista para fusionarse con `main`** una vez publicado
este commit final. La suite está completamente verde, pytest permanece aislado,
los artefactos demostrablemente obsoletos han salido del árbol, la documentación
vigente está alineada y la revisión no detecta secretos ni archivos accidentales.

## Intervención: ayuda, meteorología y saludos deterministas — 31 de julio de 2026

Estado del bloque: **completado y validado**. Los cinco fallos pendientes de la
suite anterior quedan corregidos. Esto no declara cerrada toda la auditoría:
continúan pendientes la limpieza histórica, la revisión documental global y la
revisión final de la rama antes de cualquier integración.

### Causas raíz y clasificación

1. `test_help_without_context_hides_owner_commands` — **error de producción**.
   `handle_command_help_request()` seguía llamando a
   `build_help_access_context()` con la firma anterior. Además, una búsqueda
   temática podía recuperar entradas ya filtradas y los comandos de reinicio no
   declaraban en sus metadatos que eran exclusivos del propietario.
2. `test_REDACTED_f73137d930c3_owner_sees_admin_commands` — **test desactualizado y refuerzo de
   producción**. Los comandos administrativos sí aparecían para el perfil
   propietario; el test comparaba una cabecera con capitalización distinta de la
   salida canónica en mayúsculas. La distinción entre administrador y propietario
   no estaba representada explícitamente en `HelpAccessContext`.
3. `test_weather_without_location_uses_home_location` — **error de producción**.
   La extracción tomaba todo lo situado tras el primer `en` y convertía una
   referencia temporal como `en agosto ... en mi localidad` en un topónimo.
4. `test_august_request_does_not_fake_current_forecast` — **error de producción**.
   La decisión usaba la distancia hasta el primer día del mes; si ese día entraba
   en el horizonte, se intentaba responder como si todo el mes tuviera previsión.
5. `test_common_greetings_are_deterministic` — **combinación de error de fixture
   y test desactualizado**. El doble de prueba no proporcionaba
   `GuestSessionManager` y enviaba directamente `buenos días` y `buenas noches`
   al mixin social, aunque en el flujo real pertenecen al resumen diario.

### Solución aplicada

- La ayuda sin contexto construye un contexto invitado completo y no revela
  entradas administrativas ni mediante búsqueda aproximada.
- `HelpAccessContext` separa `is_admin` de `is_owner`; las entradas
  `owner_only` requieren un propietario verificado. Los metadatos de reinicio
  declaran categoría, capacidad y visibilidad. La ejecución administrativa
  compara el identificador activo con el propietario principal configurado, sin
  coincidencias parciales ni alias textuales.
- La ubicación se extrae desde la última preposición válida y descarta meses,
  fechas relativas y expresiones como `mi localidad`, usando después el
  domicilio configurado.
- Las consultas de un mes completo y las fechas fuera de los 16 días reciben
  una explicación explícita de falta de previsión fiable. Una fecha concreta
  dentro del rango usa el pronóstico simulado disponible. El reloj puede
  inyectarse en las funciones de interpretación.
- Los saludos sociales admiten una selección de frase inyectable para tests;
  producción conserva variedad. Los tests modelan por separado saludo social,
  resumen de mañana/noche, usuario identificado, invitado y estados de sesión.

### Archivos modificados

- Producción: `console/command_help.py`, `commands/admin_policy.py`,
  `commands/restart_atlas.py`, `commands/restart_telegram.py`,
  `core/atlas_daily_brief.py` y `core/atlas_social.py`.
- Tests: `tests/test_greetings_help_biography.py`,
  `tests/test_help_owner_permissions.py`,
  `tests/test_help_permissions_contexts.py`,
  `tests/test_identity_and_help_permissions.py`,
  `tests/test_REDACTED_6915771be1c5_conversation_fixes.py` y
  `tests/test_sprint_18_7_reliability.py`.
- Documentación: este archivo y su equivalente oficial en Google Drive.

### Tests añadidos o corregidos

- Ayuda y permisos: propietario, administrador no propietario, familiar con
  capacidad autorizada, invitado, ausencia de contexto, nombre parecido no
  verificado, búsqueda temática filtrada y política exacta de ejecución.
- Meteorología: domicilio, ubicación explícita, hoy, mañana, fecha dentro del
  rango, fecha y mes fuera del rango, climatología y mención no meteorológica de
  un mes. Todos los datos meteorológicos son simulados.
- Saludos: `buenos días`, `buenas tardes`, `buenas noches`, `hola`, usuario
  identificado, invitado, sesión nueva, pendiente y existente, y selección de
  frase explícitamente inyectada.

### Resultados de validación

- Cinco tests originales, repetición 1: 5 superados en 0,17 s.
- Cinco tests originales, repetición 2: 5 superados en 0,33 s.
- Validación focal final adicional: 5 superados en 1,24 s.
- Regresiones focalizadas, dos repeticiones: 37 superados en 0,39 s y 37
  superados en 0,36 s; validación final adicional: 37 superados en 0,39 s.
- Grupos de comandos, ayuda, permisos, usuarios, perfiles, conversación,
  identidad, saludos, meteorología e interpretación: 190 superados y 21
  subtests superados en 3,76 s.
- `python -m pytest --collect-only -q`: 875 tests recopilados en 0,52 s, sin
  errores.
- `python -m pytest -q`: 875 superados, 2.324 subtests superados, 0 fallos y 0
  errores en 173,63 s.

### Confirmación de aislamiento y riesgos pendientes

El conjunto de `git status --porcelain` fue idéntico antes y después de la
suite completa: solo aparecieron los 12 archivos de código y tests modificados
intencionadamente en esta intervención. Pytest no añadió ni modificó datos
reales y no se restauró ningún archivo después de ejecutarlo.

No se contactaron Raspberry, Home Assistant, Telegram real, Ollama, servicios
externos ni dispositivos domésticos. Permanecen fuera de este bloque los
artefactos históricos ya inventariados, la limpieza general, la actualización
del resto de documentación técnica y la revisión final de la rama.

## Intervención: aislamiento de pytest e integridad de relaciones — 31 de julio de 2026

Estado del bloque: **completado**. Los fallos restantes de la suite completa no
pertenecen a persistencia de identidad, relaciones, perfiles efectivos ni
biografías.

### Causas raíz confirmadas

1. `IdentityStorage()` y `UserManager()` resolvían sus rutas predeterminadas
   directamente dentro del proyecto. Los tests unitarios de bajo nivel sí
   inyectaban carpetas temporales, pero los tests que construían `Atlas` o
   `UserManager` utilizaban esas rutas reales. Por eso una visita simulada podía
   modificar el contador y la fecha de último encuentro de `people.json`.
2. El commit de checkpoint `3e2e584` contenía dos generaciones concatenadas de
   relaciones: 255 registros creados con los UUID anteriores y 254 registros
   creados tras regenerar los UUID de las 44 personas. Los primeros 255 tenían
   al menos un extremo inexistente; los últimos 254 formaban un grafo completo,
   sin autorrelaciones ni duplicados exactos.
3. `RelationshipEngine` ya comprobaba los extremos al crear relaciones, pero
   `IdentityStorage.save_relationships()` y `add_relationship()` permitían
   persistir objetos con IDs inexistentes o con un tipo de entidad incorrecto.
4. La resolución conversacional aceptaba subsecuencias y similitud textual. Esa
   heurística podía tratar `Salvador Vicente` como `REDACTED_103e3365dd76` sin
   un alias verificado. Además, faltaba declarar `REDACTED_38b7adc65154` como
   alias verificado de `REDACTED_e3b252570a2f`.
5. El extractor de residencia de perfiles efectivos consumía también la frase
   `y ha vivido en ...`, produciendo ubicaciones derivadas incorrectas.

### Solución aplicada

- `ATLAS_IDENTITY_DATA_DIR` y `ATLAS_USER_DATA_DIR` permiten redirigir la
  persistencia sin cambiar el comportamiento de producción cuando no están
  definidas.
- `tests/conftest.py` crea un sandbox antes de la colección y una copia
  independiente por test mediante `tmp_path`. También redirige las rutas
  configurables de Telegram e incidencias de monitorización. No restaura datos
  reales: impide que se abran para escritura durante pytest.
- La capa de almacenamiento valida ambos extremos y su tipo antes de escribir
  una colección de relaciones.
- Se eliminaron mecánicamente solo los 255 registros huérfanos demostrados de
  `identity/data/relationships.json`; se conservaron intactos los 254 registros
  con extremos existentes.
- La resolución de personas conserva coincidencias exactas por nombre o alias
  y las aclaraciones basadas en relaciones verificadas, pero elimina la
  selección automática por subsecuencia o similitud. `Salvador Vicente` ya no
  se resuelve como `REDACTED_103e3365dd76`.
- `REDACTED_38b7adc65154` se añadió como alias declarativo exclusivo de `REDACTED_342ad0893cb2
  Carreres López` en la fuente familiar y en el JSON persistente.
- El extractor biográfico separa correctamente residencia actual y residencias
  anteriores.

### Archivos modificados

- Producción: `core/atlas_ai.py`, `core/user_manager.py`,
  `identity/identity_storage.py`, `identity/family_data.py`.
- Datos corregidos: `identity/data/people.json`,
  `identity/data/relationships.json`.
- Infraestructura de tests: `tests/conftest.py`.
- Tests añadidos o corregidos: `tests/test_pytest_persistence_isolation.py`,
  `tests/test_identity_storage.py`, `tests/test_family_data.py`,
  `tests/test_family_initializer.py`,
  `tests/test_person_reference_resolution.py` y
  `tests/test_conversation_identity_regressions.py`.
- Registro final: este documento.

### Validación realizada

- Aislamiento y almacenamiento, repetición 1: 9 superados en 0,31 s.
- Aislamiento y almacenamiento, repetición 2: 9 superados en 0,18 s.
- Relaciones, familia, perfiles y biografías: 126 superados, 1 test de ayuda
  ajeno al bloque deseleccionado y 2.290 subtests superados en 123,28 s.
- `python -m pytest --collect-only -q`: 863 tests recopilados en 0,48 s, sin
  errores.
- `python -m pytest -q`: 858 superados, 5 fallos, 2.324 subtests superados y 0
  errores en 176,49 s.
- Los SHA-256 de `people.json`, `animals.json` y `relationships.json` fueron
  idénticos antes y después de cada repetición y de la suite completa. El
  conjunto mostrado por `git status --porcelain` tampoco cambió durante las
  ejecuciones; no se utilizó restauración posterior.

### Riesgos y fallos pendientes

- Ayuda y permisos: 2 fallos (`test_help_without_context_hides_owner_commands`
  y `test_REDACTED_f73137d930c3_owner_sees_admin_commands`).
- Interpretación meteorológica: 2 fallos
  (`test_weather_without_location_uses_home_location` y
  `test_august_request_does_not_fake_current_forecast`).
- Saludos deterministas: 1 fallo
  (`test_common_greetings_are_deterministic`) por un fixture que no proporciona
  `guest_sessions` para `Buenas noches`.
- `tests/__tmp_conftest_pytest_temp_fixed.py` continúa como artefacto histórico
  versionado; no se eliminó porque esta intervención no autoriza limpieza
  histórica general.
- No se ejecutaron Home Assistant, Raspberry, automatizaciones reales,
  Telegram, Ollama ni pruebas remotas.

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
