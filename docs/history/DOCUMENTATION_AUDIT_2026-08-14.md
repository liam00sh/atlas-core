# Auditoría documental estructural

Esta matriz registra la revisión comparativa entre documentación, código,
configuración, tareas programadas y estado operativo. No sustituye las fuentes
de verdad: sirve como evidencia y lista de deuda documental.

## Documentos de `00 - Documentación`

| Documento | Estado anterior | Acción | Estado resultante |
|---|---|---|---|
| 01 Especificación y Arquitectura | Desactualizado parcial | Añadir referencia al mapa estructural vigente | Vigente con anexo |
| 02 Manual de Instalación Fase 1 | Histórico | Conservar | Histórico enlazado |
| 03 Constitución | Actual | Sin cambio de contenido | Actual |
| 04 Registro de Hardware | Incompleto | Mantener pendiente la validación física | Pendiente explícito |
| 05 Decisiones Técnicas | Histórico parcial | Conservar decisiones y enlazar estado vigente | Histórico enlazado |
| 06 Changelog | Incompleto | Registrar saneamiento, migración y reorganización | Actualizado |
| 07 Diseño de Atlas Core | Desactualizado parcial | Enlazar arquitectura efectiva vigente | Vigente con anexo |
| 08 Manual Atlas Core Fase 2 | Histórico | Conservar | Histórico |
| 09 Configuración y entornos | Incompleto | Añadir rutas privadas y separación de ámbitos | Actualizado |
| 10 Convenciones de desarrollo | Actual parcial | Enlazar validaciones estructurales | Actualizado |
| 11 Datos, memoria y persistencia | Incompleto | Documentar `memory_workflow`, RAG y runtime local | Actualizado |
| 12 Seguridad, privacidad y permisos | Incompleto | Añadir controles Git y exclusiones privadas | Actualizado |
| 13 Índice maestro | Desactualizado | Definir fuentes de verdad y estados | Actualizado |
| 14 Manual del Núcleo | Histórico extenso | Conservar y enlazar arquitectura vigente | Histórico enlazado |
| 15 API interna | Desactualizado parcial | Añadir alcance de API y router vigentes | Vigente con anexo |
| 16 Roadmap | Contradictorio | Corregir estado operativo y mantener Fase 6 abierta | Actualizado |
| 17 Incidencias Fase 3 | Histórico | Conservar | Histórico |
| 18 Manual técnico Fase 3 | Desactualizado parcial | Enlazar estructura v0.5.0 | Histórico enlazado |
| 19 Identidades, personalidades y modos | Actual parcial | Sin alterar detalles de voz | Sin cambio |
| 20 Personas, animales y relaciones | Actual parcial | Preservar privacidad; sin datos nuevos | Sin cambio |
| 21 IA local, prompts y contexto | Incompleto | Añadir roles, router y proveedor externo deshabilitado | Actualizado |
| 22 Pruebas, persistencia y mantenimiento | Desactualizado | Sustituir comandos y evidencia vigentes mediante anexo | Actualizado |
| 23 Instalación Fase 3 | Desactualizado | Corregir ruta operativa y tareas actuales mediante anexo | Actualizado |
| 24 Estabilización Fase 3.1 | Histórico | Conservar | Histórico |
| 25 Modelo de Seguridad | Desactualizado en estado de fase | Añadir implementación y controles actuales | Actualizado |
| 26 Atlas Tools Framework | Actual parcial | Enlazar catálogo y arquitectura vigente | Actualizado |
| 27 Beta familiar | Histórico | Conservar | Histórico |
| 28 Cerebro y conocimiento | Incompleto | Enlazar memoria y fuentes actuales | Actualizado |
| 29 Catálogo maestro de comandos | Incompleto | Aclarar código como fuente técnica y estado actual | Actualizado |
| 30 Plan Fase 5 | Histórico | Conservar | Histórico |
| 31 Automatizaciones | Actual parcial | Añadir estado operativo y límites | Actualizado |
| 32 Home Assistant en Raspberry | Desactualizado parcial | Separar guía histórica de estado verificado | Actualizado |
| 33 Backups | Desactualizado parcial | Añadir bundle y copia restaurable actuales | Actualizado |
| 34–43 Voz | Área protegida Fase 6 | No modificar | Sin cambios; Fase 6 abierta |
| 44 Auditoría y consolidación | Incompleto | Añadir cierre estructural y deuda documental | Actualizado |
| 99 Backlog | Contradictorio parcial | Conservar como backlog; Roadmap prevalece | Enlazado |
| Atlas Dataset Studio | Estado no demostrado por completo | Corregir a implementación existente con revisión humana pendiente | Actualizado |

## README de Drive

| README | Estado anterior | Acción | Estado resultante |
|---|---|---|---|
| Raíz | Desactualizado parcial | Definir PC/GitHub/Drive y estructura vigente | Actualizado |
| 01 Raspberry | Incorrecto: declaraba Raspberry como Core activo | Corregir rol y enlazar estado verificable | Actualizado |
| 02 PC | Incompleto | Identificar instalación operativa local | Actualizado |
| 03 Identidad visual | Actual | Sin cambio | Actual |
| 04 Python | Incorrecto: declaraba la copia de Drive como código activo | Marcar `atlas_core` como copia histórica privada | Actualizado |
| 05 IA local | Incompleto | Añadir roles y router | Actualizado |
| 06 Integraciones | Rutas y estados desactualizados | Corregir fuente de código y estados | Actualizado |
| 07 NAS | Pendiente explícito | Sin cambio | Pendiente |
| 08 Automatización | Incompleto | Reflejar tres tareas programadas y supervisor | Actualizado |
| 09 Interfaces | Actual parcial | Mantener voz en desarrollo | Actualizado |
| 10 Recursos | Actual | Sin cambio | Actual |
| Releases | Desactualizado | Marcar releases existentes como históricas | Actualizado |

## Deuda documental encontrada

### Corregida en esta tarea

- ruta operativa y reparto de responsabilidades PC/GitHub/Drive;
- tareas programadas y lanzadores vigentes;
- arquitectura real del repositorio sin refactorización artificial;
- roles y fallback del router local;
- exclusión de memoria workflow y runtime;
- estado histórico de la copia `04 - Python/atlas_core`;
- comandos de validación, saneamiento y evidencia reciente.

### Pendiente por falta de información o validación

- validación física periódica de restauración completa de Raspberry y Home
  Assistant;
- estado de cada dispositivo domótico no consultado durante esta tarea;
- completar revisión humana de Dataset Studio y su dataset real;
- consolidar enlaces nativos entre todos los documentos históricos de Drive.

### No tocada por pertenecer a Fase 6

- documentos 34–43;
- scripts y pruebas de voz;
- modelos, datasets, WAV, checkpoints y resultados humanos;
- selección, entrenamiento, síntesis, reproducción y personalidad definitiva.
