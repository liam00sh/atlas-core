# Atlas Core

## Versión

**0.3.1 — Fase 3.1: estabilización conversacional y validación.**

Atlas Core es el núcleo local en Python del Proyecto Atlas. Coordina usuarios, identidad conversacional, memoria, capacidades, herramientas, inteligencia artificial local y las identidades del asistente **Daxter** y **Coco**.

El proyecto está diseñado para crecer por fases sin mezclar responsabilidades ni conceder capacidades que no estén realmente disponibles.

## Requisitos

- Python 3.14 o superior.
- Git y Visual Studio Code, recomendados para desarrollo.
- Windows, Linux o Raspberry Pi OS de 64 bits.
- Ollama es opcional y solo es necesario para utilizar la IA local.
- La base actual del proyecto utiliza la biblioteca estándar de Python; las herramientas de sistema pueden incorporar dependencias opcionales en fases posteriores.

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
├── capabilities/        Capacidades realmente disponibles
├── commands/            Comandos cargados por Atlas
├── console/             Consola interactiva y resolución de comandos
├── conversation/        Conversación básica y respuestas heredadas
├── core/                Coordinación principal y mixins de Atlas
├── identity/            Personas, animales, relaciones e identidad conversacional
├── memory/              Memoria persistente, visibilidad y recuperación
├── tests/               Pruebas automatizadas
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

La versión **0.3.1** de la **Fase 3.1** queda cerrada y validada como base estable para iniciar la Fase 4. Incluye:

- identidad conversacional y separación de permisos;
- personas, animales y relaciones familiares;
- memoria autorizada y relevante;
- herramientas locales controladas;
- integración con Ollama;
- identidades Daxter y Coco;
- modos Clásico, Trabajo, Divertido y Empático;
- selección automática y bloqueo manual de modo;
- preferencias independientes por interlocutor.

La batería completa de 288 pruebas ha sido superada. La Fase 4 todavía no se ha iniciado.

## Pruebas

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Comprobación previa de sintaxis:

```bash
python -m compileall ai assistant_identity capabilities commands console conversation core identity memory tests utils
```
