# Sprint 10 — RAG documental sobre Google Drive

## Objetivo

Permitir que Atlas responda preguntas utilizando varios fragmentos del índice
local de `Atlas Project`, con fuentes visibles y sin conceder al modelo control
sobre las herramientas.

## Flujo

```text
Pregunta explícita
    ↓
Búsqueda local de fragmentos
    ↓
Selección y límite de contexto
    ↓
Prompt fundamentado
    ↓
Proveedor local (Ollama)
    ↓
Respuesta con [FUENTE N]
    ↓
Listado de documentos y enlaces
```

## Nueva capacidad

```text
documents.rag.answer
```

## Nueva herramienta

```text
tools/google_drive_rag.py
```

## Seguridad

- El modelo no busca ni abre archivos por sí mismo.
- Atlas selecciona previamente todos los fragmentos.
- Solo se usa el índice local restringido a `Atlas Project`.
- El prompt obliga a reconocer información insuficiente.
- No se sincroniza Drive automáticamente.
- No se modifica ningún archivo.
- Las fuentes se muestran aunque el modelo omita alguna cita.

## Consultas admitidas

```text
Responde usando la documentación de Drive: ¿cómo funciona la memoria?
Según la documentación de Atlas, ¿qué proveedor de IA se utiliza?
Pregunta al índice de Drive: ¿cómo está organizado el framework?
Qué dice la documentación de Atlas sobre OAuth
```

## Recuperación

El Sprint 10 utiliza recuperación léxica. Puede seleccionar varios fragmentos
del mismo documento y repartir resultados entre distintas fuentes. La búsqueda
semántica mediante embeddings queda reservada para un sprint posterior.
