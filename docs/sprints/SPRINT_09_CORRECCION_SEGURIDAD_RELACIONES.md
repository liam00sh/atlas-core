# Corrección del Sprint 9 — Seguridad de Drive y relaciones naturales

## Problemas corregidos

### 1. El índice recorría toda «Mi unidad»

La configuración OAuth se construía sin `root_folder_id`. La API terminaba
utilizando `root`, por lo que el índice podía descubrir documentos ajenos a
Atlas Project.

La integración queda ahora restringida obligatoriamente a:

```text
Atlas Project
ID: 1odTh2pF7A_HxaiAIH0h5zqcLOqHUTm3x
```

Si se intenta iniciar OAuth sin una carpeta raíz autorizada, Atlas rechaza la
configuración.

### 2. Índice antiguo contaminado

La versión del formato del índice cambia de 1 a 2. El índice antiguo queda
invalidado automáticamente y no se reutiliza. La siguiente sincronización
creará un índice nuevo limitado a Atlas Project.

### 3. Preguntas familiares delegadas a Ollama

Preguntas como estas no coincidían con los patrones deterministas:

```text
Quién es mi hermana
Cómo se llama mi novia
Quién es mi madre
Cómo se llama el hermano de Saray
Quiénes son mis hermanos
```

Al no resolverse mediante el grafo, llegaban al modelo local, que improvisaba.

Ahora se interpretan de forma determinista usando `PeopleManager` y
`RelationshipEngine`. La solución admite múltiples tipos de parentesco,
posesivos, singular, plural y referencias por nombre.

## Archivos reemplazados

```text
core/atlas_tools.py
core/atlas_ai.py
tools/google_drive_index.py
tests/test_conversation_identity_regressions.py
```

## Archivos nuevos

```text
tests/tools/test_google_drive_atlas_project_scope.py
```
