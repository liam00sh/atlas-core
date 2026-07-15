"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/mode_selector.py

Descripción:
    Selecciona el modo de personalidad más adecuado para una entrada.

    Los modos disponibles son:

        - classic:
            Conversación normal.

        - work:
            Precisión, productividad y tareas técnicas.

        - fun:
            Humor, ocio y conversaciones relajadas.

        - empathetic:
            Conversaciones personales, emocionales o delicadas.

    El selector utiliza reglas deterministas basadas en palabras
    y expresiones reconocibles.

    No utiliza todavía un modelo de inteligencia artificial.

    Este módulo no cambia directamente el modo activo.

    Únicamente devuelve una sugerencia que posteriormente podrá
    aceptar o rechazar IdentityManager.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from dataclasses import dataclass

from assistant_identity.mode import CLASSIC_MODE
from assistant_identity.mode import EMPATHETIC_MODE
from assistant_identity.mode import FUN_MODE
from assistant_identity.mode import WORK_MODE

from utils.text_normalizer import normalize_text


# =============================================================================
# RESULTADO DE SELECCIÓN
# =============================================================================

@dataclass(frozen=True)
class ModeSelection:
    """
    Representa una propuesta de modo.

    Atributos:
        mode_name:
            Nombre interno del modo sugerido.

        confidence:
            Confianza entre 0.0 y 1.0.

        reason:
            Explicación breve de la selección.

        temporary:
            Indica si el cambio debe considerarse temporal.
    """

    mode_name: str

    confidence: float

    reason: str

    temporary: bool = True

    def __post_init__(
        self,
    ) -> None:
        """
        Valida los datos de la selección.
        """

        mode_name = (
            self.mode_name
            .strip()
            .casefold()
        )

        reason = self.reason.strip()

        if mode_name not in {
            CLASSIC_MODE,
            WORK_MODE,
            FUN_MODE,
            EMPATHETIC_MODE,
        }:

            raise ValueError(
                f"Modo sugerido no válido: {mode_name}"
            )

        if not isinstance(
            self.confidence,
            (
                int,
                float,
            ),
        ):

            raise TypeError(
                "La confianza debe ser numérica."
            )

        confidence = float(
            self.confidence
        )

        if not 0.0 <= confidence <= 1.0:

            raise ValueError(
                "La confianza debe estar entre 0.0 y 1.0."
            )

        if not reason:

            raise ValueError(
                "La selección debe incluir un motivo."
            )

        object.__setattr__(
            self,
            "mode_name",
            mode_name,
        )

        object.__setattr__(
            self,
            "confidence",
            confidence,
        )

        object.__setattr__(
            self,
            "reason",
            reason,
        )


# =============================================================================
# SELECTOR
# =============================================================================

class ModeSelector:
    """
    Detecta el modo más apropiado para una entrada.

    La detección se basa en puntuaciones.

    Cada grupo de palabras suma puntos a un modo.
    El modo con mayor puntuación puede convertirse
    en una sugerencia.
    """

    MINIMUM_CONFIDENCE = 0.60

    # =========================================================================
    # PALABRAS Y EXPRESIONES DE TRABAJO
    # =========================================================================

    WORK_KEYWORDS = {
        "archivo",
        "archivos",
        "codigo",
        "programacion",
        "python",
        "linux",
        "windows",
        "servidor",
        "servidores",
        "docker",
        "base de datos",
        "sql",
        "script",
        "comando",
        "terminal",
        "powershell",
        "error",
        "fallo",
        "compilar",
        "compilacion",
        "prueba",
        "tests",
        "test",
        "documentacion",
        "documentar",
        "configuracion",
        "instalacion",
        "instalar",
        "red",
        "ip",
        "memoria ram",
        "cpu",
        "gpu",
        "disco",
        "sistema",
        "proyecto",
        "atlas",
        "trabajo",
        "trabajar",
        "estudiar",
        "estudio",
        "examen",
        "ejercicio",
        "tarea",
        "incidencia",
        "depurar",
        "debug",
        "corregir",
        "reescribir",
        "revisar el codigo",
        "paso a paso",
    }

    WORK_PHRASES = {
        "vamos a trabajar",
        "modo trabajo",
        "ponte serio",
        "necesito concentrarme",
        "vamos con el siguiente archivo",
        "corrige este archivo",
        "reescribe el archivo",
        "dime donde va",
        "explicamelo paso a paso",
        "vamos a programar",
        "vamos a estudiar",
        "tengo un error",
        "me da este fallo",
        "no compila",
        "revisa el codigo",
    }

    # =========================================================================
    # PALABRAS Y EXPRESIONES DIVERTIDAS
    # =========================================================================

    FUN_KEYWORDS = {
        "broma",
        "bromas",
        "chiste",
        "chistes",
        "diversion",
        "divertido",
        "fiesta",
        "videojuego",
        "videojuegos",
        "juego",
        "juegos",
        "fortnite",
        "fifa",
        "jak",
        "daxter",
        "crash",
        "coco",
        "sackboy",
        "littlebigplanet",
        "pelicula",
        "peliculas",
        "serie",
        "series",
        "meme",
        "memes",
        "vacilar",
        "vacile",
        "gracioso",
        "humor",
        "ocio",
        "carrera",
        "carreras",
        "aventura",
        "aventuras",
    }

    FUN_PHRASES = {
        "modo divertido",
        "modo fiesta",
        "cuentame un chiste",
        "hazme reir",
        "vamos a divertirnos",
        "estamos de fiesta",
        "quiero jugar",
        "vamos a jugar",
        "vacilame",
        "ponte gracioso",
        "di algo divertido",
    }

    # =========================================================================
    # PALABRAS Y EXPRESIONES EMPÁTICAS
    # =========================================================================

    EMPATHETIC_KEYWORDS = {
        "triste",
        "preocupado",
        "preocupada",
        "agobiado",
        "agobiada",
        "estres",
        "ansiedad",
        "ansioso",
        "ansiosa",
        "miedo",
        "asustado",
        "asustada",
        "solo",
        "sola",
        "mal",
        "fatal",
        "llorar",
        "dolor",
        "mareo",
        "mareada",
        "enfermo",
        "enferma",
        "salud",
        "problema personal",
        "discusion",
        "pelea",
        "familia",
        "pareja",
        "ruptura",
        "fallecido",
        "fallecida",
        "muerte",
        "perdida",
        "perdido",
        "frustrado",
        "frustrada",
        "cansado",
        "cansada",
        "desanimado",
        "desanimada",
        "no puedo mas",
    }

    EMPATHETIC_PHRASES = {
        "necesito hablar",
        "estoy preocupado",
        "estoy preocupada",
        "me siento mal",
        "estoy triste",
        "tengo miedo",
        "estoy agobiado",
        "estoy agobiada",
        "necesito ayuda",
        "ha pasado algo",
        "no se que hacer",
        "quiero desahogarme",
        "modo empatico",
        "habla conmigo",
        "escuchame",
        "necesito que me escuches",
    }

    # =========================================================================
    # PALABRAS Y EXPRESIONES CLÁSICAS
    # =========================================================================

    CLASSIC_PHRASES = {
        "modo clasico",
        "modo normal",
        "vuelve al modo normal",
        "vuelve al modo clasico",
        "habla normal",
        "como estas",
        "hola",
        "buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "que tal",
    }

    def select(
        self,
        text: str,
    ) -> ModeSelection:
        """
        Selecciona el modo más apropiado.

        Siempre devuelve una selección.

        Si no existe suficiente evidencia para un modo
        especial, devuelve el modo Clásico.
        """

        normalized_text = normalize_text(
            text
        )

        if not normalized_text:

            return ModeSelection(
                mode_name=CLASSIC_MODE,
                confidence=1.0,
                reason=(
                    "La entrada está vacía y se mantiene "
                    "el modo predeterminado."
                ),
                temporary=False,
            )

        # ---------------------------------------------------------------------
        # ÓRDENES MANUALES EXPLÍCITAS
        # ---------------------------------------------------------------------

        explicit_selection = (
            self._select_explicit_mode(
                normalized_text
            )
        )

        if explicit_selection is not None:

            return explicit_selection

        # ---------------------------------------------------------------------
        # PUNTUACIONES
        # ---------------------------------------------------------------------

        scores = {
            WORK_MODE: self._calculate_score(
                normalized_text,
                keywords=self.WORK_KEYWORDS,
                phrases=self.WORK_PHRASES,
            ),

            FUN_MODE: self._calculate_score(
                normalized_text,
                keywords=self.FUN_KEYWORDS,
                phrases=self.FUN_PHRASES,
            ),

            EMPATHETIC_MODE: self._calculate_score(
                normalized_text,
                keywords=self.EMPATHETIC_KEYWORDS,
                phrases=self.EMPATHETIC_PHRASES,
            ),

            CLASSIC_MODE: 0,
        }

        selected_mode = max(
            scores,
            key=scores.get,
        )

        selected_score = scores[
            selected_mode
        ]

        # Ningún modo especial ha obtenido evidencia.
        if selected_score == 0:

            return ModeSelection(
                mode_name=CLASSIC_MODE,
                confidence=0.70,
                reason=(
                    "No se ha detectado una situación "
                    "especial."
                ),
                temporary=True,
            )

        confidence = min(
            0.55 + (
                selected_score * 0.10
            ),
            1.0,
        )

        if confidence < self.MINIMUM_CONFIDENCE:

            return ModeSelection(
                mode_name=CLASSIC_MODE,
                confidence=0.60,
                reason=(
                    "La evidencia no es suficiente para "
                    "cambiar automáticamente de modo."
                ),
                temporary=True,
            )

        return ModeSelection(
            mode_name=selected_mode,
            confidence=confidence,
            reason=(
                "Se han detectado palabras o expresiones "
                f"relacionadas con el modo {selected_mode}."
            ),
            temporary=True,
        )

    def can_suggest_special_mode(
        self,
        text: str,
    ) -> bool:
        """
        Indica si la entrada sugiere un modo distinto
        del modo Clásico.
        """

        selection = self.select(
            text
        )

        return (
            selection.mode_name
            != CLASSIC_MODE
        )

    @staticmethod
    def _calculate_score(
        normalized_text: str,
        keywords: set[str],
        phrases: set[str],
    ) -> int:
        """
        Calcula la puntuación de un modo.

        Las frases completas tienen más peso
        que las palabras individuales.
        """

        score = 0

        for phrase in phrases:

            if phrase in normalized_text:

                score += 3

        normalized_words = set(
            normalized_text.split()
        )

        for keyword in keywords:

            if " " in keyword:

                if keyword in normalized_text:

                    score += 2

                continue

            if keyword in normalized_words:

                score += 1

        return score

    @staticmethod
    def _select_explicit_mode(
        normalized_text: str,
    ) -> ModeSelection | None:
        """
        Detecta una orden directa de cambio de modo.

        Estas órdenes reciben confianza máxima y no se
        consideran cambios automáticos temporales.
        """

        explicit_modes = {
            CLASSIC_MODE: {
                "modo clasico",
                "modo normal",
                "activa el modo clasico",
                "activa el modo normal",
                "vuelve al modo clasico",
                "vuelve al modo normal",
            },

            WORK_MODE: {
                "modo trabajo",
                "activa el modo trabajo",
                "ponte en modo trabajo",
                "vamos a trabajar",
                "ponte serio",
            },

            FUN_MODE: {
                "modo divertido",
                "modo fiesta",
                "activa el modo divertido",
                "activa el modo fiesta",
                "ponte divertido",
            },

            EMPATHETIC_MODE: {
                "modo empatico",
                "activa el modo empatico",
                "ponte en modo empatico",
                "quiero que seas mas comprensivo",
                "quiero que seas mas comprensiva",
            },
        }

        for mode_name, commands in explicit_modes.items():

            if normalized_text in commands:

                return ModeSelection(
                    mode_name=mode_name,
                    confidence=1.0,
                    reason=(
                        "El usuario ha solicitado "
                        "explícitamente este modo."
                    ),
                    temporary=False,
                )

        return None