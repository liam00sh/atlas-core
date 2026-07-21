# Sprint 16 — Memoria a largo plazo

Los recuerdos nuevos incorporan `importance`, `access_count`, `last_accessed_at`, `updated_at`, `history` y `state`. Los estados admitidos son `active`, `archived` y `expired`.

Las consultas léxicas registran frecuencia y última consulta. Las actualizaciones conservan el contenido previo en historial. `archive_memory` oculta un recuerdo sin borrarlo y `restore_memory` lo recupera conservando su identidad e historial.

`LongTermMemoryService` genera resúmenes persistentes por usuario y contexto, guarda los IDs de sus fuentes y permite regenerarlos sin sustituir originales. La consolidación usa similitud conservadora y devuelve únicamente propuestas `propose_merge`; no fusiona automáticamente. La política de olvido automático no está habilitada.

