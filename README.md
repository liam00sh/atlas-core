# Atlas Core

Atlas Core es el núcleo en Python del Proyecto Atlas y la base del asistente personal Daxter. Coordina la consola, los comandos, los usuarios, la memoria, la conversación básica y las capacidades disponibles, manteniendo desacopladas las futuras integraciones de IA, voz y automatización.

## Requisitos

- Python 3.14 o superior.
- Git y Visual Studio Code, recomendados para desarrollo.
- Windows, Linux o Raspberry Pi OS de 64 bits.
- En la Fase 2 no existen dependencias externas obligatorias.

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
pip install -r requirements.txt
```

## Arranque

Desde la carpeta `atlas_core`:

```bash
python main.py
```

Una vez iniciado, escribe `ayuda` para consultar los comandos disponibles o `estado` para ver el resumen del sistema.

## Estructura principal

```text
atlas_core/
├── ai/             Preparación de proveedores, modelos, prompts y herramientas
├── capabilities/   Capacidades realmente activadas
├── commands/       Comandos cargados automáticamente
├── console/        Consola y gestor de comandos
├── conversation/   Conversación básica y personalidad
├── core/           Núcleo, usuarios, versión y registro
├── memory/         Memoria persistente y permisos
├── tests/          Pruebas del proyecto
├── config.py       Configuración central
├── main.py         Punto de entrada
└── requirements.txt
```

## Filosofía

- **Local primero:** los datos y modelos deben poder permanecer en los equipos de Atlas.
- **Capacidades reales:** ninguna capa debe asumir que una función existe si está desactivada.
- **Privacidad por diseño:** la memoria utiliza propietarios, permisos y niveles de visibilidad.
- **Arquitectura modular:** cada subsistema mantiene una responsabilidad clara.
- **Evolución progresiva:** las nuevas funciones se activan por fases sin romper el núcleo estable.

## Estado actual: Fase 2

La conversación básica, los usuarios, la memoria, los comandos, el registro y el sistema de capacidades están preparados. La IA, la voz, las herramientas, Internet y la automatización continúan desactivados.

## Próximas fases

1. Integración local con Ollama y selección de modelos.
2. Construcción de contexto, prompts y memoria relevante para IA.
3. Herramientas controladas con validación y permisos.
4. Voz mediante STT y TTS.
5. Automatización, Home Assistant, API e interfaces adicionales.
