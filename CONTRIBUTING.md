# Contribuir a Atlas Core

Trabaja en una rama aislada y conserva una copia recuperable antes de cambios amplios. No incluyas `.env`, logs, conversaciones, identidades, relaciones, rutas personales, audio, datasets, modelos ni resultados humanos.

Usa exclusivamente datos inventados sin copiar la topología de relaciones reales. Los ejemplos deben poder publicarse por sí solos. Las pruebas no deben realizar llamadas reales a servicios externos ni escribir en la persistencia de una instalación.

Antes de un commit:

```bash
python -m compileall -q .
python scripts/privacy_scan.py --staged
python -m pytest -q
```

Explica en la propuesta qué cambió, qué se probó y qué artefactos privados quedaron deliberadamente fuera. Las decisiones de voz requieren revisión humana; no declares un ganador basándote solo en métricas automáticas.
