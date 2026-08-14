# Atlas Core

Atlas Core es el núcleo local en Python del Proyecto Atlas. Coordina identidad conversacional, permisos, memoria, automatización, herramientas, monitorización e IA local, manteniendo la autoridad sobre la verdad y las acciones fuera del modelo generativo.

## Estado

La versión de trabajo es **0.5.0**. Las fases 0 a 5 están cerradas. La Fase 6 —voz y personalidad— sigue abierta: la escucha humana de Round B seleccionó B1 de forma reproducible, pero la revisión emocional y de personalidad continúa pendiente. No hay una voz definitiva integrada ni se declara cerrado el entrenamiento.

El laboratorio de voz, los WAV, datasets, modelos, checkpoints y resultados humanos son artefactos privados y no forman parte de este repositorio.

## Requisitos e instalación

- Python 3.14 o superior.
- Git.
- Windows, Linux o Raspberry Pi OS de 64 bits.
- Ollama, opcional, solo para IA local.

```bash
git clone <URL_PUBLICA_DEL_REPOSITORIO>
cd atlas_core
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Activa el entorno con `.venv\Scripts\activate` en Windows o `source .venv/bin/activate` en Linux. Después:

```bash
python main.py
```

## Datos privados

El repositorio público no contiene personas, relaciones, hogares, credenciales, conversaciones ni preferencias reales. Una instalación privada puede configurar:

```text
ATLAS_PRIVATE_DATA_DIR=<directorio privado fuera del repositorio>
ATLAS_FAMILY_DATA_FILE=<ruta opcional a family.json>
ATLAS_USER_PROFILES_FILE=<ruta opcional a users.json>
ATLAS_HOUSEHOLD_DATA_FILE=<ruta opcional a households.json>
ATLAS_IDENTITY_DATA_DIR=<persistencia de identidad>
ATLAS_USER_DATA_DIR=<persistencia por usuario>
```

Si no se aportan esos datos, Atlas arranca con colecciones privadas vacías y un perfil genérico seguro; no inventa identidades. Los esquemas ficticios de `examples/private_runtime/` sirven únicamente para desarrollo y pruebas. Copia `.env.example` a un fichero local ignorado y nunca confirmes el `.env` real.

Consulta [docs/PRIVACY_ARCHITECTURE.md](docs/PRIVACY_ARCHITECTURE.md) para el contrato de separación y [SECURITY.md](SECURITY.md) para comunicar vulnerabilidades.

El mapa de responsabilidades entre la copia operativa, GitHub y Google Drive,
así como las rutas que deben conservar compatibilidad, está en
[docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md).

## Arquitectura

```text
atlas_core/
├── ai/                  Router, proveedores locales, prompts y herramientas
├── assistant_identity/  Identidades Daxter/Coco y modos
├── automation/          Automatización segura y adaptadores simulables
├── authorization/       Decisiones y políticas de autorización
├── capabilities/        Catálogo de capacidades disponibles
├── commands/            Comandos y confirmaciones
├── console/             Interfaz de consola
├── conversation/        Contexto y continuidad conversacional
├── core/                Coordinación principal
├── daily_life/          Funciones cotidianas desacopladas
├── identity/            Modelos y motores; sin datos personales incluidos
├── knowledge/           Recuperación y conocimiento
├── memory/              Persistencia y visibilidad
├── monitoring/          Salud, incidencias y recuperación autorizada
├── telegram_interface/  Canal desacoplado del núcleo
├── atlas_dataset_studio/ Herramienta local de revisión de dataset
├── examples/            Datos enteramente ficticios
├── scripts/             Diagnóstico, validación y controles preventivos
├── tools/               Herramientas registradas y adaptadores
└── tests/               Pruebas aisladas y sin servicios de pago
```

Principios operativos:

- local primero y servicios externos desacoplados;
- permisos asociados a la persona autenticada;
- una explicación nunca ejecuta una acción;
- el fallback de voz entrega la respuesta, pero no repite la acción del núcleo;
- persistencia atómica e idempotente;
- pruebas con proveedores, dispositivos y datos simulados;
- revisión humana obligatoria para decisiones de voz.

## Verificación

```bash
python -m compileall -q .
python scripts/privacy_scan.py
python -m pytest -q
```

Para activar el control local antes de cada commit:

```bash
python -m pip install pre-commit
pre-commit install
```

La lista privada `privacy_blocklist.txt` es local e ignorada. Se crea a partir de los términos que la instalación no debe publicar. El ejemplo versionado no contiene información real. El flujo de CI ejecuta el escáner sobre el árbol y el historial disponible.

Las pruebas redirigen identidad, perfiles, Telegram, conocimiento y monitorización a directorios temporales. No requieren Internet, APIs de pago, Google Drive, Telegram real ni una Raspberry Pi.

## Contribución

Antes de proponer cambios, lee [CONTRIBUTING.md](CONTRIBUTING.md). No abras una incidencia pública con secretos o datos personales. Los artefactos privados de voz y dataset se coordinan por los canales privados del proyecto.

## Licencia

El repositorio no declara todavía una licencia de redistribución. Hasta que se añada una, el código conserva todos los derechos de su titular.
