# Corrección conversacional de Atlas

Archivos incluidos:

- `family_data.py`
- `atlas_ai.py`
- `system_prompt.py`
- `test_conversation_identity_regressions.py`

## Sustitución

Copia cada archivo sobre su ruta correspondiente:

- `identity/family_data.py`
- `core/atlas_ai.py`
- `ai/prompts/system_prompt.py`
- `tests/test_conversation_identity_regressions.py`

Haz antes una copia de seguridad de los archivos actuales.

## Validación

```powershell
python -m compileall core identity ai tests
python -m unittest tests.test_conversation_identity_regressions -v
python -m unittest tests.test_family_data -v
python -m unittest tests.test_relationship_engine -v
python -m unittest discover -s tests -p "test_*.py" -v
```

Después elimina las cachés de Python y reinicia Atlas.
