# Changelog — Sprint 12

## Añadido

- Paquete `knowledge/` para recuperación unificada de conocimiento.
- Modelo común `KnowledgeFragment`.
- Etiquetas de procedencia para memoria, personas, relaciones y documentos.
- Adaptador de memoria personal autorizada.
- Adaptador de personas y relaciones verificadas.
- Adaptador del índice léxico de Google Drive.
- Adaptador del índice semántico de Google Drive.
- Recuperador común con aislamiento de errores por fuente.
- Ranking con prioridades por autoridad, verificación y actualidad.
- Eliminación de duplicados mediante contenido normalizado y procedencia.
- Clasificación de sensibilidad.
- Exclusión de información sensible por defecto.
- Permiso independiente `knowledge.sensitive.read`.
- Enmascarado de valores sensibles autorizados.
- Detección conservadora de conflictos estructurados.
- Resolución por prioridad y confirmación en empates.
- Constructor de contexto con límites de fragmentos, caracteres y fuente.
- Servicio `KnowledgeService`.
- Herramienta `atlas.knowledge`.
- Capacidad `knowledge.retrieve`.
- Capacidad `knowledge.answer`.
- Reconocimiento determinista de preguntas naturales.
- Seguimiento conversacional «¿De dónde sabes eso?».
- Conservación de las fuentes de la última respuesta por usuario.
- Respuesta de insuficiencia cuando no existen fuentes autorizadas.
- Manejo controlado de proveedor local ausente, fallido o vacío.
- Pruebas del núcleo, adaptadores y conversación.

## Modificado

- `core/atlas.py` registra y configura el recuperador, servicio y herramienta.
- `core/atlas.py` integra la conversación unificada antes de la respuesta
  general de IA.
- `core/atlas_tools.py` incorpora el controlador conversacional de conocimiento.
- `tools/atlas_adapter.py` mantiene la compatibilidad del framework con la nueva
  capacidad.

## Correcciones de integración

- `IdentityKnowledgeSource` utiliza el contrato real de
  `RelationshipEngine.get_relationships_for_entity()` con `entity_id` y
  `PERSON_ENTITY`.
- Los errores internos de los adaptadores quedan aislados.
- El texto de excepciones potencialmente sensible no se almacena ni se muestra.
- Los errores del proveedor local se convierten en respuestas estructuradas.
- Las respuestas vacías del proveedor se consideran insuficientes.
- Se ampliaron variantes naturales sin conceder al modelo control sobre
  herramientas.

## Seguridad

- Drive continúa en modo lectura.
- El acceso permanece restringido a `Atlas Project`.
- No se copian documentos dentro de la memoria personal.
- No se otorgan permisos sensibles automáticamente.
- No se registran contenidos de excepciones internas.
- No se modifica información persistente al detectar conflictos.
- Las credenciales y los índices continúan fuera del código fuente.

## Compatibilidad

- Se conserva `self.tool_registry`.
- Se conserva `self.tool_selector`.
- Se conserva `self.framework_tool_registry`.
- Se conserva `self.tool_manager`.
- Se conserva `self.framework_tool_adapter`.
- No se modifica `main.py`.
- Se mantienen el RAG, el índice léxico y el índice semántico.
- Se mantienen las relaciones familiares verificadas.

## Pruebas

Añadidos:

```text
tests/knowledge/test_knowledge_core.py
tests/knowledge/test_knowledge_sources.py
tests/knowledge/test_knowledge_conversation.py
```

Las pruebas cubren recuperación, ranking, privacidad, conflictos, límites de
contexto, aislamiento de fallos, adaptadores reales y comprensión natural.
