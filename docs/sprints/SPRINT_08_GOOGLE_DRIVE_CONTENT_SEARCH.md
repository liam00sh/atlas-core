# Sprint 8 — Búsqueda por contenido en Google Drive

## Objetivo

Permitir que Atlas encuentre información aunque el usuario no recuerde el
nombre del documento.

## Nueva capacidad

```text
documents.search_content
```

La capacidad:

1. localiza documentos candidatos mediante Google Drive;
2. lee únicamente documentos textuales;
3. compara el contenido de forma tolerante a mayúsculas y acentos;
4. extrae un fragmento alrededor de la coincidencia;
5. puntúa y ordena los resultados;
6. conserva el nombre y el enlace de la fuente.

## Ejemplos

```text
Dónde hablamos de memoria persistente en Drive
En qué documento aparece OAuth en Drive
Busca dentro de Drive sistema de permisos
Busca dónde se habla de Ollama en Drive
```

Respuesta esperada:

```text
[1] 05 - Decisiones Técnicas
    ...fragmento relevante...
    Fuente: https://...
```

Después puede utilizarse:

```text
Abre el primero
Resume esos fragmentos
¿Qué decisión se tomó?
```

## Arquitectura

```text
Conversación
    ↓
GoogleDriveConversationController
    ↓
documents.search_content
    ↓
GoogleDriveReadTool
    ↓
GoogleDriveApiClient
    ↓
Drive API fullText + lectura textual
    ↓
Fragmentos con fuente
```

## Seguridad y límites

- Solo lectura.
- Respeta `google.drive.read`.
- Máximo 30 documentos candidatos por consulta conversacional.
- Máximo 10 resultados.
- Fragmentos de aproximadamente 700 caracteres.
- Ignora archivos binarios o no compatibles.
- La IA no ejecuta directamente la herramienta.
- No se crea todavía una base vectorial permanente.

## Compatibilidad

Se mantienen sin cambios:

```text
documents.search
documents.read
folders.list
```

También se conserva el estado por usuario del Sprint 7.
