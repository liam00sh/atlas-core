# Estructura y responsabilidades del Proyecto Atlas

## Fuentes de verdad

| Ámbito | Ubicación | Responsabilidad |
|---|---|---|
| Ejecución operativa | `C:\Proyectos\Atlas\atlas_core` | Código en ejecución, configuración local y estado runtime. |
| Código compartible | `https://github.com/liam00sh/atlas-core` | Código, pruebas, documentación técnica y ejemplos ficticios saneados. |
| Documentación completa | `Atlas Project` en Google Drive | Manuales, decisiones, histórico y recursos del proyecto. |
| Datos privados | Rutas locales/Drive autorizadas | Identidad, memoria, integraciones y configuración real; nunca GitHub. |
| Voz y personalidad | Laboratorios y `12 - Voz` | Trabajo activo de Fase 6, fuera del alcance de reorganizaciones generales. |

La copia operativa no depende del clon histórico conservado en
`Atlas Project/04 - Python/atlas_core`. Ese árbol de Drive contiene estado y
evidencia anteriores y no se usa como repositorio Git operativo.

## Repositorio operativo

La estructura modular actual se conserva porque los entrypoints, imports,
pruebas y tareas programadas dependen de ella. Encapsularla artificialmente en
un paquete adicional aumentaría el riesgo sin mejorar el contrato público.

```text
atlas_core/
├── ai/                    modelos, proveedor local y router explicable
├── assistant_identity/    identidades del asistente y modos
├── atlas_dataset_studio/  aplicación local e independiente de revisión
├── authorization/         decisiones y políticas de autorización
├── automation/            motor seguro y adaptadores de automatización
├── capabilities/          catálogo de capacidades
├── commands/              comandos, ayuda y confirmaciones
├── console/               interfaz de consola
├── conversation/          contexto y continuidad conversacional
├── core/                  coordinación determinista principal
├── daily_life/            funciones cotidianas desacopladas
├── identity/              modelos de identidad, sin datos reales publicados
├── knowledge/             recuperación y conocimiento
├── memory/                memoria con visibilidad y persistencia configurable
├── monitoring/            supervisor, incidencias, probes y widgets
├── telegram_interface/    canal Telegram desacoplado
├── voice/                 interfaz de voz en desarrollo, Fase 6 abierta
├── scripts/               instalación, operación, validación y diagnóstico
├── tools/                 herramientas registradas
├── tests/                 pruebas aisladas y regresiones
├── docs/                  documentación técnica pública
├── data/                  estado local o ejemplos según subruta
├── runtime/               estado operativo privado, ignorado por Git
├── main.py                entrada del núcleo
└── atlas_*_launcher.py    entradas de servicio y escritorio
```

## Compatibilidad operativa

Las tareas programadas usan la ruta fija `C:\Proyectos\Atlas\atlas_core`:

- `Proyecto Atlas - Escritorio` ejecuta `atlas_desktop_launcher.py`;
- `Proyecto Atlas - Monitorizacion` ejecuta
  `scripts/run_monitoring_background.ps1`;
- `Proyecto Atlas - Telegram` ejecuta
  `scripts/start_telegram_background.ps1`.

Por ello permanecen en la raíz `main.py`, `config.py`, `logger.py` y los tres
launchers. Las herramientas especializadas viven bajo `scripts/`; los
diagnósticos manuales viven bajo `scripts/diagnostics/` y las incidencias
documentadas bajo `docs/troubleshooting/`.

## IA local

El contrato estable usa roles, no nombres físicos: `fast`, `reasoning` y
`deep`. La configuración predeterminada los resuelve mediante Ollama a
`qwen2.5:7b`, `qwen2.5:14b` y `qwen3:30b`. El router combina contexto,
referencias, ambigüedad, memoria, relaciones, herramientas, temporalidad,
criticidad y volumen recuperado. El rol `external` permanece deshabilitado.

## Datos privados y runtime

`.env`, `data/private/`, `data/memory_workflow/` y `runtime/` son locales y
están excluidos de Git. Las pruebas redirigen persistencia a directorios
temporales o ejemplos ficticios. No se deben copiar datos personales, tokens,
memoria real, modelos, datasets, WAV o checkpoints a documentación pública.

## Drive

La raíz numerada existente se conserva porque separa documentación,
infraestructura, software histórico, IA, integraciones, automatización,
interfaces, recursos, backups y voz con un nivel de profundidad pequeño. No se
renumeran carpetas solo por estética. `11 - Backups` y `12 - Voz` son áreas
protegidas y quedan fuera de cualquier movimiento estructural general.
