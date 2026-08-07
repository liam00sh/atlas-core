# Guía de etiquetado de Daxter

La expresión oficial es exactamente una de: `neutral`, `sonriente`, `picaro`, `sorprendido`, `pensativo`, `emocionado`, `asustado`, `enfadado`, `curioso`, `confiado`, `risa`, `cansado`, `sonoliento`, `determinado` o `travieso`.

Escuche la interpretación, no deduzca solo por el texto. Use confianza baja cuando dos expresiones sean plausibles y `needs_second_review` si otra escucha puede cambiar la decisión. Energía describe activación vocal; intensidad describe la fuerza de la emoción. Son independientes.

La intención tiene un único valor controlado. Use `indeterminada` si no hay evidencia suficiente, no como sustituto de una segunda revisión.

## Personalidad

Active `personality_usable` cuando la frase aporte un patrón de carácter, vocabulario o reacción reutilizable. Añada varias etiquetas solo cuando cada una esté respaldada. `personality_reason` debe explicar brevemente el valor de la frase. Reserve `iconica` para líneas excepcionalmente representativas, no simplemente conocidas.

`conversation_use` describe funciones que la frase ayuda a estudiar; admite varios valores. Una frase competitiva y humorística puede usar `competicion` y `humor` a la vez.

## Calidad y TTS

El dataset de partida está limpio, pero la escucha humana decide calidad y utilidad. `tts_usable=true` no equivale a aceptada: la exportación TTS exige además `accepted` o `accepted_with_notes`. Use `excluded` para material que no deba entrenarse y documente el motivo.

Nunca corrija silenciosamente `text`. Una falta o adaptación se registra en `normalized_text`, dejando visible la transcripción verificada.
