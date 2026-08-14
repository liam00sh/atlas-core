# Corrección de zonas horarias en Windows

Python en Windows no incluye normalmente la base IANA usada por `zoneinfo`.
Instala las dependencias con:

```powershell
python -m pip install -r requirements.txt
```

O directamente:

```powershell
python -m pip install tzdata==2026.3
```

Después repite:

```powershell
python -m pytest .\tests\telegram\test_interuser_delivery.py -q
```

El código incluye un fallback seguro a UTC para que Atlas no se caiga si falta
`tzdata`, pero para recordatorios correctos en Europe/Madrid debe instalarse.
