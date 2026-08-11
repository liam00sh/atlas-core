# Arquitectura de privacidad

## Límite público y privado

GitHub contiene código, pruebas, esquemas ficticios y documentación técnica compartible. Google Drive y los directorios locales privados contienen documentación interna, datos personales, historiales, credenciales, datasets, audio, modelos, checkpoints y resultados humanos.

El código no presupone que los datos privados estén dentro del checkout. Las rutas se suministran mediante variables de entorno y las cargas toleran que los ficheros no existan. Una ausencia produce colecciones vacías o un perfil genérico; nunca una copia incorporada de los datos de una persona.

```text
Repositorio público
    ├── código y validadores
    ├── pruebas aisladas
    └── examples/private_runtime (100 % ficticio)

Directorio privado externo
    ├── family.json
    ├── users.json
    ├── households.json
    ├── identity/
    ├── assistant/preferences.json
    └── datos operativos por usuario y canal
```

## Reglas de persistencia

- `ATLAS_PRIVATE_DATA_DIR` define la raíz privada recomendada.
- Las variables específicas prevalecen sobre la raíz general.
- Los ficheros privados no se restauran después de una prueba: se impide que la prueba los abra como destino.
- Los fixtures copian los ejemplos públicos a un directorio temporal diferente para cada prueba.
- Los inicializadores son idempotentes y validan referencias antes de persistir.
- Los WAV y textos verificados del dataset no se modifican silenciosamente.

## Controles preventivos

`scripts/privacy_scan.py` revisa rutas prohibidas, formatos de secretos y una lista local de términos privados. No imprime el valor de un secreto. El hook de pre-commit analiza lo preparado y CI repite el control. La revisión de publicación debe añadir además un escáner especializado de secretos y recorrer todas las referencias e historial reescrito.

Un resultado limpio no demuestra por sí solo que un repositorio sea publicable. También se revisan nombres de fichero, metadatos de commit, topologías familiares seudonimizadas, rutas privadas, archivos binarios, ramas y etiquetas.

## Voz y dataset

Los scripts públicos pueden describir contratos y reproducibilidad, pero nunca incorporan voces, audio generado, modelos, dataset, claves ciegas ni hojas humanas completadas. La similitud automática es evidencia auxiliar; la selección final depende de escucha humana ciega. El fallback de entrega de voz no vuelve a ejecutar la acción ya decidida por Atlas Core.
