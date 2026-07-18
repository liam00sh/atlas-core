# Atlas 0.3.1 — cierre de Fase 3.1

La documentación nativa de Google Drive y las notas de versión ya se han actualizado.

Sustituye estos archivos dentro de `04 - Python/atlas_core`:

- `README.md`
- `core/version.py`
- `commands/version.py`
- `tests/test_prompt_builder.py`

No se ha modificado nada dentro de `11 - Backups`.

Después ejecuta:

```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

Get-ChildItem -Recurse -File -Include "*.pyc","*.pyo" |
    Remove-Item -Force

python -m compileall ai assistant_identity capabilities commands console conversation core identity memory tests utils
python -m unittest discover -s tests -p "test_*.py" -v
python main.py
```

El banner y el comando `version` deben mostrar `0.3.1`.
