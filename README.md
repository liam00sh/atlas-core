# Atlas Core

## Versión

**0.5.0 — Fase 6: voz y personalidad en desarrollo.**

Atlas Core es el núcleo local en Python del Proyecto Atlas. Coordina usuarios, identidad conversacional, memoria, capacidades, herramientas, inteligencia artificial local y las identidades del asistente **Daxter** y **Coco**.

El proyecto está diseñado para crecer por fases sin mezclar responsabilidades ni conceder capacidades que no estén realmente disponibles.

## Requisitos

- Python 3.14 o superior.
- Git y Visual Studio Code, recomendados para desarrollo.
- Windows, Linux o Raspberry Pi OS de 64 bits.
- Ollama es opcional y solo es necesario para utilizar la IA local.
- Las dependencias de ejecución y pruebas están declaradas en `requirements.txt`; la integración opcional de Google Drive utiliza `requirements-google-drive.txt`.

## Instalación

```bash
git clone <URL_DEL_REPOSITORIO>
cd atlas_core
python -m venv .venv
```

Activación del entorno virtual:

```bash
# Windows
.venv\Scripts\activate

# Linux / Raspberry Pi OS
source .venv/bin/activate
```

Instalación reproducible de dependencias:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Arranque

Desde la carpeta `atlas_core`:

```bash
python main.py
```

Una vez iniciado, escribe `ayuda` para consultar los comandos disponibles o `estado` para mostrar el resumen del sistema.

## Estructura principal

```text
atlas_core/
├── ai/                  Proveedores, modelos, prompts, contexto, caché y herramientas
├── assistant_identity/  Identidades Daxter/Coco, modos y bancos de frases
├── automation/          Automatizaciones seguras y adaptadores domésticos
├── capabilities/        Capacidades realmente disponibles
├── commands/            Comandos cargados por Atlas
├── console/             Consola interactiva y resolución de comandos
├── conversation/        Conversación básica y respuestas heredadas
├── core/                Coordinación principal y mixins de Atlas
├── daily_life/          Servicios cotidianos, agenda y meteorología
├── identity/            Personas, animales, relaciones e identidad conversacional
├── knowledge/           Recuperación semántica y conocimiento documental
├── memory/              Memoria persistente, visibilidad y recuperación
├── monitoring/          Salud, incidencias y supervisión local
├── telegram_interface/  Canal Telegram desacoplado del núcleo
├── tests/               Pruebas automatizadas
├── tools/               Nuevo framework modular de herramientas
├── utils/               Normalización y utilidades compartidas
├── config.py            Configuración central
├── main.py              Punto de entrada
└── requirements.txt     Dependencias reproducibles
```

## Principios de diseño

- **Local primero:** los datos y modelos deben poder permanecer en los equipos de Atlas.
- **Privacidad por diseño:** los permisos pertenecen a la persona que habla, no a quien mantiene abierta la sesión.
- **Capacidades reales:** ninguna capa debe afirmar que puede realizar una acción desactivada.
- **Identidad separada del modo:** Daxter y Coco conservan su personalidad; los modos solo ajustan temporalmente su comportamiento.
- **Persistencia idempotente:** los inicializadores pueden ejecutarse varias veces sin duplicar entidades ni relaciones.
- **Arquitectura modular:** cada módulo mantiene una responsabilidad concreta.

## Estado actual

La versión oficial activa es **0.5.0**. Las fases 0 a 5 están cerradas y la Fase 6 —voz y personalidad— permanece en desarrollo. El núcleo integra ya herramientas, memoria documental, Telegram, automatización segura y monitorización, manteniendo proveedores externos opcionales y desacoplados.

## Pruebas

Batería principal:

```bash
python -m pytest -q
```

Colección sin ejecución:

```bash
python -m pytest --collect-only -q
```

Comprobación previa de sintaxis:

```bash
python -m compileall ai assistant_identity capabilities commands console conversation core identity memory tests tools utils
```
