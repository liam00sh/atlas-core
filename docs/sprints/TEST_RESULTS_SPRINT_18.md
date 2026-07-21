# Resultados de pruebas — Sprint 18

## Línea base anterior

Ejecutada antes de editar:

```text
python -m pytest tests -q
544 passed
2324 subtests passed
0 failed
635.84 s
```

## Suite Telegram

La suite usa clientes, reloj, núcleo y respuestas simulados. No utiliza token,
Internet ni Telegram real.

```text
python -m pytest tests/telegram -q
78 passed
0 failed
6.15 s
```

Suites de regresión específicas:

```text
python -m pytest tests/memory -q
48 passed in 13.27 s

python -m pytest tests/knowledge -q
18 passed in 1.05 s

python -m pytest tests/tools -q
165 passed in 17.49 s
```

## Comprobación offline

```text
python scripts/check_telegram_config.py --offline
Telegram activado: False
Token presente: False
Almacenamiento accesible: si
Integracion con Atlas disponible: si
Conexion real: omitida (--offline)
```

## Regresión final

```text
python -m pytest tests -q
622 passed
2324 subtests passed
0 failed
688.78 s (00:11:28)
```

El incremento frente a la línea base es de 78 pruebas. No se eliminó ninguna
prueba heredada y el número de subtests permanece en 2324.
