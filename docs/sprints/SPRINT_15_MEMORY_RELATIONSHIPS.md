# Sprint 15 — Relaciones entre recuerdos

`MemoryLinkStore` persiste enlaces `related_to`, `part_of`, `belongs_to_project`, `supports`, `contradicts`, `supersedes` y `derived_from`.

Todo enlace exige dos recuerdos del mismo usuario, explicación y evidencia. No existe una ruta para que el modelo persista relaciones por sí solo. Los enlaces son idempotentes, explicables y quedan fechados.

La navegación parte de coincidencias léxicas y recorre enlaces verificados para formar contexto. `LinkedMemoryKnowledgeSource` incorpora ese contexto a `KnowledgeRetriever`. La detección conservadora de contradicciones solo compara claves estructuradas y devuelve `propose_review`; nunca elimina ni modifica recuerdos.

