# Sprint 17 — Optimización conservadora

## Cambios aplicados

### Caché de IdentityStorage

- Clave: ruta absoluta de `people.json`, `animals.json` o `relationships.json` más firma `(mtime_ns, tamaño)`.
- Propietario: una instancia de `IdentityStorage`.
- Duración: vida de la instancia mientras la firma no cambie.
- Invalidación: toda escritura propia y cualquier cambio externo de firma.
- Límite: tres entradas.
- Privacidad: permanece local, no contiene resultados conversacionales y nunca se comparte entre instancias; cada lectura devuelve copias profundas.

La caché no cambia el formato persistente ni evita escrituras, atomicidad o validación.

### Inicialización familiar

`FamilyInitializer` carga una vez las relaciones existentes, construye claves estructurales y resuelve cada referencia única una sola vez. Si una relación ya existe, omite exclusivamente la ruta redundante de volver a buscarla, contarla y crearla. Cuando falta, utiliza `RelationshipEngine.create_relationship()` con los mismos argumentos y mantiene inversas, validaciones y errores.

## Cambios descartados

- Lazy loading de OAuth/Drive: riesgo de cambiar restauración y primera respuesta.
- Caché de respuestas o KnowledgeRetriever: riesgo de permisos, sesiones y datos obsoletos.
- Caché de Ollama: no se midieron llamadas duplicadas.
- Reducir fuentes, contexto, relaciones o límites: degradaría calidad.
- Asincronía, multiproceso o refactor general: complejidad no justificada.
- Devolver objetos mutables compartidos desde identidad: más rápido, pero inseguro ante modificaciones sin guardar.
- Agrupar escrituras de auditoría o frecuencia: podría perder persistencia tras un fallo.

## Compatibilidad

No cambian contratos públicos, formatos JSON, permisos, respuestas, fallbacks, herramientas, Drive, Ollama, RAG, memoria ni selección de capacidades. `main.py` permanece intacto y ambos sistemas de herramientas siguen presentes.

