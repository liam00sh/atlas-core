"""Excepciones del subsistema de voz."""


class VoiceError(RuntimeError):
    """Error base del subsistema de voz."""


class VoiceNotFoundError(VoiceError):
    """La voz solicitada no existe en el catálogo."""


class VoiceUnavailableError(VoiceError):
    """La voz existe, pero no está disponible."""


class TTSProviderError(VoiceError):
    """El proveedor TTS no pudo completar la síntesis."""
