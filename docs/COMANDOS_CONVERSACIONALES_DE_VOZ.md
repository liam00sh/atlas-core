# Comandos conversacionales de voz

## Objetivo

Permitir que el usuario autenticado consulte y cambie sus preferencias de voz
sin utilizar la CLI externa.

## Comandos disponibles

```text
voz
voz estado
voz daxter oficial
voz daxter alex
voz daxter santa
voz coco oficial
voz coco dora
voz velocidad 1.10
voz volumen 0.80
voz fallback activar
voz fallback desactivar
```

## Límites

- velocidad: entre 0.75 y 1.35;
- volumen: entre 0.10 y 1.00.

## Persistencia

Los cambios se guardan en:

```text
data/voice/user_preferences.json
```

La preferencia pertenece al usuario autenticado.

## Compatibilidad

El flujo de comandos admite ahora argumentos. Los comandos antiguos sin
argumentos conservan su funcionamiento.
