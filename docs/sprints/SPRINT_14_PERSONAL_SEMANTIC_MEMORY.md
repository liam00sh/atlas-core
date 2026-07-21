# Sprint 14 — Memoria semántica personal

Se incorpora `PersonalMemorySemanticIndex`, persistido separadamente en `data/knowledge/personal_memory_semantic.json`. Reutiliza el contrato local de embeddings de Ollama, mantiene entradas por propietario y combina 75 % de similitud vectorial con 25 % de coincidencia léxica.

`MemoryManager` notifica altas, modificaciones y eliminaciones a observadores aislados. El índice actualiza solo recuerdos cuyo hash o modelo cambió y una caída del proveedor de embeddings nunca impide escribir la memoria principal.

`PersonalSemanticMemoryKnowledgeSource` integra los resultados con `KnowledgeRetriever`. Los recuerdos sensibles se clasifican antes de devolverse y requieren autorización explícita. El índice de Drive no se modifica ni comparte almacenamiento.

