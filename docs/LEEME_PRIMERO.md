# Corrección de identidad conversacional y consultas meta

Incluye:

- interlocutor temporal persistente por sesión Telegram;
- separación de autenticación e interlocutor;
- `Soy Noa, qué sabes de mí` dividido en identidad y consulta;
- vuelta al propietario con `soy Liam`, `he vuelto`, `ya estoy yo`, etc.;
- consultas `quién soy`, `con quién hablo` y `en qué modo estás`;
- saludo `¿estás?`;
- desambiguación al saludar a una persona presente;
- corrección mecanográfica conservadora para palabras de intención;
- eliminación de etiquetas de visibilidad en respuestas Telegram;
- `qué sabes de mí` consulta la memoria del interlocutor temporal.

No modifica `main.py` ni mezcla los registros de herramientas legacy/framework.
