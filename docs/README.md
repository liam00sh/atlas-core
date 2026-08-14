# Documentación de Atlas Core

Este índice cubre la documentación pública y técnica que vive junto al código.
La documentación operativa completa y los datos privados pertenecen a la raíz
canónica `Atlas Project` de Google Drive; no se duplican en Git.

## Referencias vigentes

- [Estructura y responsabilidades](architecture/PROJECT_STRUCTURE.md): mapa del
  repositorio, compatibilidad de rutas y separación PC/GitHub/Drive.
- [Arquitectura de privacidad](PRIVACY_ARCHITECTURE.md): frontera entre código
  público, configuración local y datos privados.
- [Monitorización y recuperación](MONITORIZACION_Y_RECUPERACION.md): supervisor,
  incidencias, widgets y recuperación controlada.
- [Servicio Telegram supervisado](SERVICIO_TELEGRAM_SUPERVISADO.md): ciclo de
  vida del canal y límites operativos.
- [Arquitectura de IA](ARQUITECTURA_IA_MULTIMODELO_Y_CONVERSACION.md): roles de
  modelos, router y continuidad conversacional.
- [Atlas Dataset Studio](dataset_studio/ATLAS_DATASET_STUDIO.md): entrada a la
  documentación de la herramienta local de revisión humana.

## Organización

- `architecture/`: arquitectura transversal vigente.
- `dataset_studio/`: manual, esquema, recuperación y pruebas de Dataset Studio.
- `troubleshooting/`: incidencias reproducibles y su resolución.
- `sprints/`: especificaciones y resultados históricos por sprint.
- `history/`: auditorías e informes que conservan trazabilidad y no sustituyen
  las referencias vigentes.

Los documentos relacionados con voz y personalidad se mantienen donde están
mientras la Fase 6 siga abierta. No deben moverse ni fusionarse como parte de
una reorganización general.

## Criterio de vigencia

El código y las pruebas son la fuente técnica de verdad. En Drive, el índice
maestro identifica la fuente humana principal de cada área. Un informe fechado
o un documento de sprint conserva evidencia histórica, pero no prevalece sobre
la arquitectura, los manuales vigentes, el Roadmap o el Changelog actuales.
