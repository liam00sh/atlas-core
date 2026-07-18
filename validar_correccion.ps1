$ErrorActionPreference = "Stop"

Write-Host "Limpiando cachés de Python..."
Get-ChildItem -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

Get-ChildItem -Recurse -File -Include "*.pyc","*.pyo" |
    Remove-Item -Force

Write-Host "Compilando..."
python -m compileall core identity tests

Write-Host "Ejecutando pruebas prioritarias..."
python -m unittest tests.test_family_data -v
python -m unittest tests.test_family_initializer -v
python -m unittest tests.test_conversation_identity_regressions -v
python -m unittest tests.test_conversation_regressions -v
python -m unittest tests.test_phase_3_1_data_integrity -v

Write-Host "Ejecutando suite completa..."
python -m unittest discover -s tests -p "test_*.py" -v
