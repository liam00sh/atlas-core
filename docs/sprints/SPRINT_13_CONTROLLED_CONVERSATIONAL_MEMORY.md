# Sprint 13 — Aprendizaje conversacional controlado

## Objetivo

Sprint 13 añade un ciclo seguro de detección, propuesta, confirmación y escritura. La detección nunca modifica la memoria. `KnowledgeRetriever` conserva su responsabilidad de lectura y ve los cambios confirmados mediante el mismo `MemoryManager`.

## Arquitectura

- `CandidateDetector` aplica reglas conservadoras, clasifica categoría, temporalidad y sensibilidad, y rechaza preguntas, hipótesis, ficción, terceros y secretos.
- `MemoryProposalStore` conserva propuestas aisladas por `user_id` y sesión, con caducidad y estados idempotentes. El JSON se reemplaza atómicamente.
- `MemoryWorkflowService` comprueba duplicados y valores exclusivos contradictorios, y coordina altas, cambios, relaciones estructuradas y bajas.
- `MemoryAuditLog` registra eventos mínimos en JSONL y omite valores sensibles.
- `MemoryWorkflowTool` convierte cada intención en una capacidad del framework con permisos por operación.
- `MemoryWorkflowConversation` reconoce confirmaciones y rechazos inequívocos, correcciones, consultas y borrados. El estado pendiente nunca se comparte entre usuarios.

Flujo:

```text
mensaje -> detector -> propuesta pendiente -> confirmación explícita
        -> permiso reevaluado -> MemoryManager/RelationshipEngine -> auditoría
```

## Propuestas, actualización y borrado

Una propuesta caduca a los diez minutos por defecto. Confirmarla dos veces devuelve el resultado previo y no duplica recuerdos. Confirmación, rechazo y modificación validan conjuntamente `proposal_id`, `user_id` y `session_id`. Rechazarla no escribe memoria y minimiza inmediatamente el contenido si era sensible.

Antes de escribir, la propuesta pasa a `processing`. Cada recuerdo confirmado conserva `proposal_id` como clave idempotente. Si Atlas se interrumpe entre la escritura, el resultado, la auditoría y el cierre, el siguiente intento reconcilia el resultado existente y termina el flujo sin repetir la operación ni el evento de auditoría.

Los campos exclusivos conocidos, como color favorito o residencia, generan una propuesta de sustitución cuando ya existe un valor. Una corrección explícita localiza un único recuerdo y muestra el valor anterior y el nuevo. El borrado también exige una propuesta. Si hay varias coincidencias se conserva un estado `delete_selection` sin objetivo; frases como «El primero», «Borra el número 2» o «Me refiero al tercero» lo convierten en una propuesta concreta que todavía requiere confirmación.

Las relaciones reconocibles, como «Saray es mi pareja», se encaminan a `RelationshipEngine` con `confirmed=True`, siempre que ambas personas puedan resolverse. No se duplican como texto libre.

## Permisos y riesgos

| Capacidad | Permiso | Riesgo |
|---|---|---|
| consultar | `memory.read` | bajo |
| consultar datos sensibles | `memory.sensitive.read` | alto |
| proponer/rechazar/corregir propuesta | `memory.propose` | bajo |
| confirmar alta o relación | `memory.write` | medio |
| proponer/confirmar actualización | `memory.update` | medio |
| proponer/confirmar eliminación | `memory.delete` | alto |
| consultar auditoría | `memory.audit.read` | alto |
| confirmar dato sensible | `memory.sensitive.write` | alto |

El adaptador normal concede los permisos no sensibles solo a una persona estructurada con estado `user`. Un visitante no obtiene acceso. `memory.sensitive.read` y `memory.sensitive.write` no se conceden automáticamente desde CLI.

## Privacidad y procedencia

Contraseñas, tokens, claves API, códigos de recuperación, tarjetas y CVV no generan propuestas. Datos médicos o financieros solo se consideran ante una orden explícita; requieren permiso sensible y confirmación reforzada. El log general enmascara entradas que parecen secretos. La auditoría y los metadatos sustituyen el texto sensible por una marca.

`memory.read` filtra también recuerdos heredados mediante la clasificación de privacidad del Sprint 12. Una consulta general excluye los fragmentos sensibles. Una consulta explícita exige `memory.sensitive.read` y devuelve el contenido protegido, no el valor completo.

Cada recuerdo confirmado conserva categoría, sensibilidad, temporalidad, texto de origen autorizado, interfaz, `proposal_id`, confirmación y fuente `confirmed_conversation`. Las consultas posteriores lo ven sin reiniciar Atlas y sin tocar índices de Drive.

## Conversación

Se admiten órdenes como «Recuerda que…», candidatos conservadores como «Mi color favorito es…», confirmaciones inequívocas, rechazo, corrección antes de guardar, consulta, actualización de un recuerdo único y solicitud de olvido. Una respuesta ambigua no confirma. El controlador conserva por usuario y sesión los IDs de los últimos recuerdos mostrados; «¿De dónde recuerdas eso?» utiliza únicamente ese contexto y nunca el último recuerdo global.

## Persistencia

- Memoria real: `memory/data/memories.json` (almacén existente).
- Flujo auxiliar: `data/memory_workflow/proposals.json` y `audit.jsonl`.
- `data/memory_workflow/` está excluido de Git.

## Límites conocidos

- La CLI no dispone todavía de un resolvedor interactivo que conceda `memory.sensitive.read` o `memory.sensitive.write`; el soporte existe para interfaces autorizadas futuras.
- La clasificación conversacional es deliberadamente conservadora y no pretende comprender cualquier paráfrasis.
- No se implementa restauración de borrados; el evento queda preparado para una futura recuperación.
- La equivalencia semántica avanzada y las contradicciones en prosa libre siguen requiriendo mejoras futuras.
- La temporalidad se clasifica, pero el cálculo completo de `valid_until` para expresiones naturales queda pendiente.

## Pruebas

Las pruebas cubren detección y falsos positivos, ausencia de escritura durante la propuesta, aislamiento, caducidad, idempotencia, procedencia, duplicados, sustitución, corrección, borrado, selección múltiple, privacidad, permisos, conversación, reinicio y resultados estructurados de herramienta.

Resultado final del 19 de julio de 2026: `470 passed, 2324 subtests passed, 0 failed`. Los cuatro comandos y sus tiempos están registrados en `docs/sprints/TEST_RESULTS_SPRINT_13.md`.
