# Sistema de prompts

Este directorio contiene las instrucciones y constructores que preparan el
prompt enviado al modelo de inteligencia artificial.

## Componentes

### `system_prompt.py`

Define únicamente las reglas generales y permanentes: precisión, privacidad,
seguridad, uso responsable de capacidades y formato de respuesta.

### `builder.py`

Construye el prompt final combinando:

- identidad activa del asistente: Daxter o Coco;
- modo activo: clásico, trabajo, divertido o empático;
- interlocutor real y usuario autenticado;
- permisos e identidad conversacional;
- capacidades disponibles;
- información real del sistema;
- recuerdos autorizados;
- conversación reciente;
- mensaje actual.

### `tool_prompt.py`

Prepara instrucciones específicas para la selección y ejecución controlada de
herramientas.

## Regla de diseño

La identidad y los permisos no deben quedar fijados en el prompt base. Se
inyectan dinámicamente después de haber sido resueltos por los gestores de
Atlas.
