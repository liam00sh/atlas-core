# Evidencias de validación

## Descripción

Esta carpeta almacena las evidencias generadas durante la ejecución de la suite de pruebas de Atlas Core.

Su finalidad es conservar un registro visual de las validaciones realizadas al finalizar cada fase del proyecto, permitiendo verificar el estado funcional del sistema en un momento concreto del desarrollo.

Las evidencias no forman parte del código fuente ni de la documentación técnica, sino que constituyen un complemento de verificación del proceso de desarrollo.

## Contenido

En esta carpeta pueden almacenarse, entre otros:

- Capturas de la ejecución completa de la suite de pruebas.
- Resultados finales de compilación (`compileall`).
- Validaciones del script `clean_and_test.ps1`.
- Evidencias de regresión tras la corrección de incidencias.
- Capturas utilizadas para documentar el cierre de una fase.

## Convención de nombres

Se recomienda utilizar el siguiente formato:

```
AAAA-MM-DD_descripción.png
```

Ejemplos:

```
2026-07-15_tests_fase3_ok.png
2026-07-15_compileall_ok.png
2026-07-15_clean_and_test_ok.png
```

## Buenas prácticas

- Conservar únicamente las evidencias finales de cada fase o hito importante.
- Evitar almacenar capturas de errores temporales que ya hayan sido resueltos.
- No modificar las evidencias una vez archivadas.
- Mantener nombres descriptivos y orden cronológico para facilitar su consulta.

---

**Proyecto Atlas**  
**Atlas Core – Evidencias de validación**