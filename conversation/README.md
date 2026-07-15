# Conversación

Este paquete contiene la conversación local basada en reglas y los componentes
históricos de intención y respuesta que pueden funcionar sin un modelo de IA.

La identidad activa del asistente, sus modos de comportamiento y sus bancos de
frases se gestionan en `assistant_identity/`. Los módulos de personalidad que
permanecen en esta carpeta se conservan por compatibilidad con código anterior
y no deben utilizarse para nuevas integraciones.

## Responsabilidades actuales

- Resolver intenciones y respuestas locales simples.
- Mantener compatibilidad con la conversación básica sin IA.
- Proporcionar mensajes de denegación y respuestas auxiliares usadas por el
  núcleo.

La identidad conversacional de las personas, sus permisos y relaciones se
gestionan desde `identity/`.
