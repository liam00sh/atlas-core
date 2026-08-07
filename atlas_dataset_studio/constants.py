from __future__ import annotations

EMOTIONS = (
    "neutral", "sonriente", "picaro", "sorprendido", "pensativo",
    "emocionado", "asustado", "enfadado", "curioso", "confiado",
    "risa", "cansado", "sonoliento", "determinado", "travieso",
)
EMOTION_LABELS = {
    "neutral": "Neutral", "sonriente": "Sonriente", "picaro": "Pícaro",
    "sorprendido": "Sorprendido", "pensativo": "Pensativo",
    "emocionado": "Emocionado", "asustado": "Asustado",
    "enfadado": "Enfadado", "curioso": "Curioso", "confiado": "Confiado",
    "risa": "Risa", "cansado": "Cansado", "sonoliento": "Soñoliento",
    "determinado": "Determinado", "travieso": "Travieso",
}
INTENTIONS = (
    "afirmacion", "pregunta", "orden", "aviso", "saludo", "despedida",
    "celebracion", "queja", "burla", "explicacion", "reaccion",
    "exclamacion", "narracion", "relleno_interjeccion", "indeterminada",
)
CONFIDENCE = ("alta", "media", "baja")
LEVELS = ("baja", "media", "alta")
PERSONALITY_STRENGTH = ("baja", "media", "alta", "iconica")
PERSONALITY_TAGS = (
    "humor", "sarcasmo", "burla", "presumido", "impulsivo", "travieso",
    "valiente", "cobarde_comico", "leal", "afectivo", "quejica", "dramatico",
    "competitivo", "entusiasta", "curioso", "ingenioso", "charlatan",
    "autorreferencial", "coletilla", "reaccion_caracteristica",
)
CONVERSATION_USES = (
    "saludo", "despedida", "confirmacion", "negacion", "pregunta",
    "respuesta_corta", "respuesta_larga", "humor", "burla", "celebracion",
    "queja", "advertencia", "reaccion", "interjeccion", "explicacion",
    "motivacion", "competicion", "afecto", "curiosidad", "relleno", "otro",
)
QUALITY = ("excelente", "buena", "aceptable", "limite", "excluir")
REVIEW_STATUS = (
    "pending_review", "needs_second_review", "accepted", "accepted_with_notes",
    "excluded", "superseded",
)
REVIEWED_STATUS = frozenset({"accepted", "accepted_with_notes", "excluded", "superseded"})

CORE_FIELDS = (
    "sample_id", "audio_file", "relative_path", "text", "normalized_text",
    "original_normalized_text", "source_game", "duration_seconds", "sample_rate",
    "channels", "sample_width_bits", "sha256", "emotion", "emotion_confidence",
    "emotion_source", "intention", "energy", "emotion_intensity",
    "personality_usable", "personality_tags", "personality_reason",
    "personality_strength", "conversation_use", "tts_usable", "quality",
    "review_status", "review_notes", "needs_human_review", "text_modified",
    "updated_at", "reviewed_at",
)
