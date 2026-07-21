# Sprint 12 — Memoria documental unificada

## 1. Objetivo

El Sprint 12 crea una capa común de recuperación de conocimiento para Proyecto
Atlas sin mezclar físicamente los repositorios existentes.

Atlas puede consultar de forma coordinada:

- memoria personal autorizada;
- personas estructuradas;
- relaciones verificadas;
- índice documental léxico de Google Drive;
- índice semántico de Google Drive;
- proveedor local de inteligencia artificial.

La memoria, la identidad y los índices de Drive conservan sus ubicaciones y
contratos actuales. La nueva capa `knowledge/` actúa únicamente como
coordinadora de lectura.

## 2. Arquitectura implementada

```text
memory/                         identity/
   │                               │
   └──────────────┬────────────────┘
                  │
data/integrations/google_drive/
                  │
                  ▼
             knowledge/
                  │
        ┌─────────┴─────────┐
        │                   │
knowledge.retrieve   knowledge.answer
        │                   │
        └─────────┬─────────┘
                  ▼
          Respuesta con fuentes
```

La implementación se distribuye en:

```text
knowledge/
    __init__.py
    fragment.py
    privacy.py
    conflict.py
    context_builder.py
    sources.py
    retriever.py
    service.py
    conversation.py

tools/
    knowledge.py
```

La integración se realiza desde:

```text
core/atlas.py
core/atlas_tools.py
```

## 3. Modelo común de conocimiento

`KnowledgeFragment` representa cualquier resultado recuperado mediante una
estructura neutral.

Contiene:

- `source_type`: clase de procedencia;
- `source_id`: identificador original;
- `title`: título legible;
- `content`: contenido recuperado;
- `score`: relevancia normalizada;
- `metadata`: datos adicionales de procedencia;
- `verified`: indica si la fuente está verificada;
- `sensitive`: identifica información sensible.

Tipos de fuente contemplados:

```text
memory
person
relationship
drive_document
semantic_chunk
system_fact
conversation_context
```

Cada fragmento conserva su procedencia y dispone de una etiqueta legible, por
ejemplo:

```text
[MEMORIA]
[PERSONA VERIFICADA]
[RELACION VERIFICADA]
[DOCUMENTO]
[FRAGMENTO SEMANTICO]
```

## 4. Fuentes de solo lectura

### 4.1 Memoria

`MemoryKnowledgeSource` reutiliza el recuperador de memoria existente y
mantiene:

- propietario;
- visibilidad;
- confirmación;
- sensibilidad;
- puntuación de relevancia.

No copia memorias a otro repositorio.

### 4.2 Personas y relaciones

`IdentityKnowledgeSource` consulta `PeopleManager` y `RelationshipEngine`.

Recupera:

- personas mencionadas por nombre o alias;
- relaciones vinculadas;
- nivel de confianza;
- confirmación;
- procedencia de la relación.

Las relaciones verificadas conservan prioridad frente a documentos en prosa.

### 4.3 Índice documental

`DriveIndexKnowledgeSource` utiliza el índice léxico local de Google Drive.

Conserva:

- ID del documento;
- nombre;
- fragmento;
- posición;
- fecha de modificación;
- enlace de Drive.

### 4.4 Índice semántico

`SemanticKnowledgeSource` utiliza el índice semántico del Sprint 11.

Si el índice semántico no está disponible, el fallo queda aislado y las demás
fuentes pueden seguir respondiendo.

## 5. Recuperación, ranking y deduplicación

`KnowledgeRetriever` consulta todas las fuentes autorizadas y aplica:

1. aislamiento de errores por fuente;
2. filtrado de privacidad;
3. normalización de puntuaciones;
4. prioridad por tipo de fuente;
5. bonificación por verificación;
6. bonificación por actualidad;
7. eliminación de duplicados;
8. orden estable;
9. límite final de resultados;
10. detección de conflictos.

Prioridad general:

```text
relationship
person
memory
system_fact
drive_document
semantic_chunk
conversation_context
```

Una relación verificada tiene prioridad sobre una afirmación documental
ambigua, aunque el documento posea una puntuación léxica alta.

Los errores internos de una fuente se registran únicamente mediante:

```text
source_type
error_type
```

No se conserva el texto de la excepción para evitar filtrar información
sensible.

## 6. Privacidad

`KnowledgePrivacyFilter` clasifica información como:

```text
none
personal
financial
medical
secret
```

La clasificación puede proceder de metadatos explícitos o de una detección
defensiva.

Por defecto, los datos sensibles se excluyen.

Para recuperarlos deben cumplirse simultáneamente:

1. la consulta debe pedirlos expresamente;
2. el contexto debe disponer del permiso:

```text
knowledge.sensitive.read
```

Cuando están autorizados, se enmascaran por defecto mediante:

```text
[DATO PROTEGIDO]
```

El permiso sensible no se concede automáticamente por utilizar la CLI, Drive o
la herramienta general de conocimiento.

## 7. Detección de conflictos

`detect_conflicts()` compara afirmaciones estructuradas que incluyan:

```text
subject
predicate
value
```

Cuando aparecen valores incompatibles:

- se conserva el conflicto;
- se prioriza la fuente con mayor autoridad;
- una fuente verificada precede a una no verificada;
- un empate exige confirmación;
- la memoria no se modifica automáticamente.

La detección es deliberadamente conservadora. No intenta inferir
contradicciones libres en cualquier texto para evitar falsos positivos.

## 8. Construcción del contexto

`KnowledgeContextBuilder` limita el contenido enviado al proveedor local.

Aplica:

- máximo de fragmentos;
- máximo de caracteres;
- máximo por fuente concreta;
- diversidad documental;
- truncado controlado;
- etiquetas de procedencia.

No se envía toda la memoria ni todos los documentos a Ollama.

## 9. Servicio y herramienta

`KnowledgeService` coordina:

1. recuperación;
2. privacidad;
3. ranking;
4. conflictos;
5. construcción del contexto;
6. generación local;
7. fuentes;
8. insuficiencia estructurada.

La herramienta `atlas.knowledge` declara:

```text
knowledge.retrieve
knowledge.answer
```

Permiso general:

```text
knowledge.read
```

Permiso adicional para datos sensibles:

```text
knowledge.sensitive.read
```

Si el proveedor local no está disponible, falla o devuelve una respuesta
vacía, Atlas devuelve una insuficiencia controlada en lugar de propagar una
excepción.

## 10. Conversación natural

`KnowledgeIntentRecognizer` reconoce preguntas como:

```text
¿Qué sabes sobre mi familia?
¿Qué información tienes sobre Saray?
¿Cómo quiero que funcione la memoria de Atlas?
¿Qué hemos decidido sobre la privacidad?
Resume lo que sabes sobre la arquitectura de Atlas.
Háblame de Saray.
Dime todo lo que recuerdas sobre mi familia.
Junta lo que sabes sobre el acceso a Internet.
¿Hay información contradictoria sobre esta persona?
```

También admite el seguimiento:

```text
¿De dónde sabes eso?
```

Atlas conserva las fuentes de la última respuesta unificada por usuario y puede
mostrarlas posteriormente.

La selección continúa siendo determinista: el modelo local no recibe control
directo sobre las herramientas.

## 11. Compatibilidad

El Sprint 12 conserva:

```text
self.tool_registry
self.tool_selector
self.framework_tool_registry
self.tool_manager
self.framework_tool_adapter
```

También conserva:

- el sistema heredado;
- el framework nuevo;
- la integración de Drive en lectura;
- la restricción a `Atlas Project`;
- el RAG de los Sprints 10 y 11;
- el índice léxico;
- el índice semántico;
- las relaciones verificadas;
- `main.py` sin modificaciones.

## 12. Pruebas incluidas

```text
tests/knowledge/__init__.py
tests/knowledge/test_knowledge_core.py
tests/knowledge/test_knowledge_sources.py
tests/knowledge/test_knowledge_conversation.py
```

Cubren:

- combinación de fuentes;
- eliminación de duplicados;
- prioridad de relaciones verificadas;
- actualidad documental;
- privacidad;
- enmascarado;
- conflictos;
- límites de contexto;
- aislamiento de adaptadores;
- contrato real de `RelationshipEngine`;
- procedencia documental;
- reconocimiento conversacional;
- consultas sensibles;
- seguimiento de fuentes.

## 13. Límites conocidos

- La contradicción libre en prosa no se deduce automáticamente.
- Drive no se sincroniza automáticamente.
- El índice semántico debe existir para aportar resultados semánticos.
- El permiso sensible no se concede por defecto.
- Las fuentes se consultan en lectura y no se copian a una base unificada.
- Las respuestas dependen de la disponibilidad del proveedor local para su
  redacción final.
