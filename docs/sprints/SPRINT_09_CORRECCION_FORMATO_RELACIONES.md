# Corrección Sprint 9 — Formato de relaciones familiares

## Error localizado

La resolución del grafo familiar encontraba correctamente las personas, pero
el patrón de relaciones se construía sin agrupar sus alternativas:

```text
hermana|hermano|madre|novia|...
```

Al integrarlo dentro de expresiones mayores, la precedencia de `|` provocaba
que `mi hermana`, `mi madre` o `mi novia` no coincidieran de forma completa.
Por eso se generaban frases como:

```text
La hermana de  es...
El madre de  es...
La novia de  es...
```

## Cambios

- Agrupadas todas las alternativas con `(?:...)`.
- Restaurados `Tu` y `Tus` para relaciones directas.
- Añadido género gramatical explícito para `madre` y demás relaciones.
- Conservados artículos dentro de cadenas familiares.
- Resueltos nombres abreviados a sus nombres canónicos.
- Unificado el formato de relaciones directas y encadenadas.
- Añadidas pruebas específicas para el patrón, los artículos y las frases
  anidadas.

## Ejemplos esperados

```text
Quién es mi hermana
→ Tu hermana es REDACTED_65dc3df1f2c0.

Quién es mi madre
→ Tu madre es REDACTED_ba2c2b03ba9a.

Cómo se llama mi novia
→ Tu novia es REDACTED_8762331d93e2.

Cómo se llama el hermano de REDACTED_bc04a68d9192
→ El hermano de REDACTED_8762331d93e2 es REDACTED_7b2ab41fc4b5.

Cómo se llama la hija de la tía de REDACTED_bc04a68d9192
→ La hija de la tía de REDACTED_8762331d93e2 es REDACTED_91f6198b34bc.
```
