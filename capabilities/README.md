# Sistema de capacidades

Este módulo define qué funciones están disponibles realmente
en la instalación actual de Atlas.

Su objetivo es evitar que otras partes del proyecto utilicen
funciones que todavía no existen o que se encuentran desactivadas.

## Capacidades actuales

| Capacidad | Estado |
|-----------|--------|
| Conversación | ✅ |
| Memoria | ✅ |
| IA | ❌ |
| Voz | ❌ |
| Herramientas | ❌ |
| Automatización | ❌ |
| Internet | ❌ |

## Uso

```python
atlas.can_use_ai()

atlas.can_use_voice()

atlas.can_use_memory()
```
