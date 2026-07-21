# Sprint 11 — Búsqueda semántica e intenciones naturales de Drive

## Objetivos

1. Añadir un índice semántico persistente mediante embeddings locales.
2. Mejorar el RAG del Sprint 10 con recuperación híbrida.
3. Evitar que listado y estado dependan de comandos exactos.

## Índice semántico

Se guarda en:

```text
data/integrations/google_drive/semantic_index.json
```

Utiliza por defecto:

```text
nomic-embed-text
```

El índice semántico se genera a partir del índice documental local; no vuelve a
leer Drive ni modifica documentos.

## Recuperación híbrida

El RAG intenta primero:

```text
búsqueda semántica
```

Si el índice no existe, Ollama no está disponible o la consulta falla, utiliza
automáticamente:

```text
búsqueda léxica del Sprint 10
```

Así, el Sprint 11 no rompe el funcionamiento anterior.

## Intenciones naturales

El controlador ya no exige una orden idéntica. Reconoce, entre otras:

```text
Mostrar el listado de Drive
Enséñame qué hay en Drive
Dime los archivos de Drive
Quiero ver el contenido de Atlas Project
Muéstrame cómo está el índice
Dime el estado de la indexación
```

## Comandos semánticos

```text
Actualiza el índice semántico de Drive
Muéstrame el estado del índice semántico
Busca semánticamente en Drive cómo funciona la memoria
```

## Seguridad

- Sigue limitado a `Atlas Project`.
- Ollama funciona localmente.
- Los vectores se guardan en `data/integrations/google_drive/`.
- No se envía documentación a servicios externos.
- El modelo no controla las herramientas.
