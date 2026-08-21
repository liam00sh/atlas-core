# Fase 6 Voz — auditoría E2E 13/13 y pulido final

## Estado

La batería física se ejecutó y valoró en sus 13 casos. Esto no cierra la Fase 6:
la aceptación final de límites TTS queda pendiente de una mini validación humana ciega.

## Causa y corrección TTS

- Los WAV generados, reproducidos y preservados coinciden; playback no introdujo los cortes.
- El techo fijo de 110 tokens podía finalizar sin token de parada. El runtime elimina el último
  token porque en una salida normal es el cierre, pero al alcanzar el techo eliminaba habla real.
- Los 80 ms finales se añadían después de esa pérdida y no podían recuperar el fonema.
- Sin pre-roll, el fundido inicial de 5 ms podía aplicarse sobre habla real.
- La política candidata usa presupuesto dinámico acotado a 120–260 tokens, segmentación
  semántica a 120 caracteres, 40 ms de pre-roll y 200 ms de margen final.
- La traza conserva tokens presupuestados/usados, señal de límite alcanzado y métricas por unidad.

El laboratorio compara 80/120/160/200/250 ms de margen final, 0/20/40/60 ms de pre-roll,
segmentación natural y el candidato completo. La elección final sigue siendo humana.

## Correcciones funcionales

- La frase de voz `Recuérdame mañana que a las 18.30 revise Atlas` crea ahora un recordatorio
  persistente en lugar de caer en conversación general.
- `Saluda a Lidia` entra en conversación social dirigida antes del comando difuso `saludar`.
- Reiniciar Telegram crea una confirmación peligrosa real. `cancelar` la elimina antes de toda
  ejecución; confirmar consume el estado antes de lanzar el reinicio.
- El diagnóstico de Home Assistant muestrea a 0, 0,25, 0,5, 1, 2, 3, 5, 10, 15 y 30 segundos.
  Atlas mantiene el fallo honesto si la API no refleja el estado físico.
- La ausencia de Docker en PATH continúa comunicándose como ejecutable no disponible.
- Los hotwords STT siguen siendo contextuales; no se añadió ninguna sustitución global.

## Reproducción del mini-laboratorio

La herramienta `tools/build_voice_e2e_boundary_lab.py` recibe de forma explícita la evidencia,
el runtime, el modelo y la referencia privados. Genera `BLIND_PLAYER.html`, una hoja CSV vacía
para la valoración, una clave ciega separada y un manifiesto técnico. Ninguno de estos artefactos
privados se versiona.

La Fase 6 permanece abierta hasta que la mini prueba ciega acepte una variante TTS.
