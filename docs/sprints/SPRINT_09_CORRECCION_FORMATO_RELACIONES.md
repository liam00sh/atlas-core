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
→ Tu hermana es Lidia Vicente Martínez.

Quién es mi madre
→ Tu madre es María José Martínez Sanz.

Cómo se llama mi novia
→ Tu novia es Saray Izquierdo Carreres.

Cómo se llama el hermano de Saray
→ El hermano de Saray Izquierdo Carreres es Rubén Izquierdo Carreres.

Cómo se llama la hija de la tía de Saray
→ La hija de la tía de Saray Izquierdo Carreres es Noa Melinte Carreres.
```
