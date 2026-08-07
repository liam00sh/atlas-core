# Esquema del dataset

Atlas Dataset Studio importa CSV y JSONL v1 sin repetir el escaneo. Preserva todos los campos desconocidos para que una migración no pierda información. En el primer guardado crea un snapshot del archivo original y añade los campos de v2 que falten.

## Identidad y audio

- `sample_id`: identificador único y estable.
- `audio_file`, `relative_path`: nombre y ruta relativa; nunca absoluta.
- `source_game`: juego de origen.
- `duration_seconds`, `sample_rate`, `channels`, `sample_width_bits`, `sha256`: metadatos técnicos.

## Texto

- `text`: transcripción verificada e inmutable desde la interfaz.
- `normalized_text`: versión editable.
- `original_normalized_text`: valor de restauración capturado al importar.
- `text_modified`: indica divergencia respecto al valor original.

## Expresión e intención

- `emotion`, `emotion_confidence`, `emotion_source`.
- `intention`, `energy`, `emotion_intensity`.

Las listas controladas se definen en `constants.py` y en el preset `daxter_es`.

## Personalidad y conversación

- `personality_usable`: utilidad para corpus de personalidad.
- `personality_tags`: etiquetas múltiples separadas por `|` en CSV.
- `personality_reason`, `personality_strength` (`baja`, `media`, `alta`, `iconica`).
- `conversation_use`: valores múltiples separados por `|`.

## Calidad y revisión

- `tts_usable`, `quality`, `review_status`, `review_notes`, `needs_human_review`.
- `updated_at`, `reviewed_at`: marcas temporales UTC.

Solo `accepted` y `accepted_with_notes` con `tts_usable=true` entran en `tts_dataset.jsonl`. Solo `personality_usable=true` entra en `personality_dataset.jsonl`.

