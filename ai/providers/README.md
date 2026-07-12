# Proveedores de IA

Los proveedores permiten que Atlas se comunique con distintos motores de inteligencia artificial sin depender directamente de uno concreto.

## Archivos

### `base_provider.py`

Define la interfaz común que deben implementar todos los proveedores.

### `ollama_provider.py`

Contendrá la futura integración con Ollama.

## Métodos comunes

Todo proveedor deberá implementar:

- `is_available()`
- `generate(prompt)`
- `get_provider_name()`

## Estado

Ningún proveedor está conectado actualmente.
