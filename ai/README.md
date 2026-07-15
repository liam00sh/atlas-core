# Inteligencia artificial

Este paquete agrupa la integración de Atlas con modelos locales, proveedores,
prompts, contexto conversacional, caché y herramientas controladas.

## Componentes

- `providers/`: comunicación con proveedores locales, como Ollama.
- `models/`: registro y selección de modelos disponibles.
- `prompts/`: construcción segura del prompt final.
- `context/`: historial temporal separado por interlocutor.
- `cache/`: reutilización controlada de respuestas y resúmenes.
- `tools/`: herramientas que consultan datos reales del sistema o ejecutan
  acciones permitidas.

## Principios

- El modelo no decide por sí solo qué permisos tiene una persona.
- Las capacidades declaradas deben coincidir con funciones realmente
  disponibles.
- La identidad activa del asistente y su modo se incorporan dinámicamente.
- Los recuerdos y contextos solo se incluyen tras aplicar las reglas de acceso.
- Una respuesta nunca debe afirmar que se ejecutó una acción cuando Atlas no la
  realizó.

El resultado final puede ser generado por Daxter o Coco, según las preferencias
del interlocutor y el estado de `IdentityManager`.
