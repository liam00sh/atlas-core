"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/phrase_bank.py

Descripción:
    Define el banco de frases utilizado por las identidades del asistente.

    Un PhraseBank almacena frases organizadas por categorías.

    Ejemplos de categorías:

        greetings:
            Saludos.

        farewells:
            Despedidas.

        startup:
            Inicio de Atlas.

        shutdown:
            Cierre de Atlas.

        thinking:
            Mientras se prepara una respuesta o acción.

        waiting:
            Mientras se espera una operación.

        success:
            Una tarea ha terminado correctamente.

        error:
            Una operación ha fallado.

        warning:
            Existe algún riesgo o advertencia.

        memory_saved:
            Se ha guardado un recuerdo.

        memory_found:
            Se ha recuperado un recuerdo.

        confirmation_requested:
            Se necesita permiso antes de continuar.

        confirmation_accepted:
            El usuario ha autorizado una acción.

        confirmation_rejected:
            El usuario ha rechazado una acción.

        mode_changed:
            Se ha cambiado de modo.

        identity_changed:
            Se ha cambiado de identidad.

        encouragement:
            Mensajes de ánimo.

        compliments:
            Comentarios positivos.

        jokes:
            Bromas generales.

        idle:
            Frases para momentos de inactividad.

    Cada identidad tendrá su propio PhraseBank:

        - Daxter.
        - Coco.

    PhraseBank no:

        - Decide cuándo utilizar una frase.
        - Cambia la identidad activa.
        - Cambia el modo.
        - Construye el prompt.
        - Guarda preferencias.
        - Ejecuta acciones.

    Únicamente almacena, valida y selecciona frases.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import random

from dataclasses import dataclass
from dataclasses import field


# =============================================================================
# CATEGORÍAS
# =============================================================================

GREETINGS = "greetings"
FAREWELLS = "farewells"

STARTUP = "startup"
SHUTDOWN = "shutdown"

THINKING = "thinking"
WAITING = "waiting"
IDLE = "idle"

SUCCESS = "success"
ERROR = "error"
WARNING = "warning"

MEMORY_SAVED = "memory_saved"
MEMORY_FOUND = "memory_found"

CONFIRMATION_REQUESTED = "confirmation_requested"
CONFIRMATION_ACCEPTED = "confirmation_accepted"
CONFIRMATION_REJECTED = "confirmation_rejected"

MODE_CHANGED = "mode_changed"
IDENTITY_CHANGED = "identity_changed"

ENCOURAGEMENT = "encouragement"
COMPLIMENTS = "compliments"
JOKES = "jokes"
GAME_QUOTES = "game_quotes"


PHRASE_CATEGORIES = {
    GREETINGS,
    FAREWELLS,
    STARTUP,
    SHUTDOWN,
    THINKING,
    WAITING,
    IDLE,
    SUCCESS,
    ERROR,
    WARNING,
    MEMORY_SAVED,
    MEMORY_FOUND,
    CONFIRMATION_REQUESTED,
    CONFIRMATION_ACCEPTED,
    CONFIRMATION_REJECTED,
    MODE_CHANGED,
    IDENTITY_CHANGED,
    ENCOURAGEMENT,
    COMPLIMENTS,
    JOKES,
    GAME_QUOTES,
}


# =============================================================================
# NOMBRES LEGIBLES
# =============================================================================

PHRASE_CATEGORY_LABELS = {
    GREETINGS: "Saludos",
    FAREWELLS: "Despedidas",
    STARTUP: "Inicio",
    SHUTDOWN: "Cierre",
    THINKING: "Pensando",
    WAITING: "Espera",
    IDLE: "Inactividad",
    SUCCESS: "Éxito",
    ERROR: "Error",
    WARNING: "Advertencia",
    MEMORY_SAVED: "Recuerdo guardado",
    MEMORY_FOUND: "Recuerdo encontrado",
    CONFIRMATION_REQUESTED: "Confirmación solicitada",
    CONFIRMATION_ACCEPTED: "Confirmación aceptada",
    CONFIRMATION_REJECTED: "Confirmación rechazada",
    MODE_CHANGED: "Cambio de modo",
    IDENTITY_CHANGED: "Cambio de identidad",
    ENCOURAGEMENT: "Ánimo",
    COMPLIMENTS: "Cumplidos",
    JOKES: "Bromas",
    GAME_QUOTES: "Frases originales de los juegos",
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def is_valid_phrase_category(
    category: str,
) -> bool:
    """
    Indica si una categoría de frases es válida.
    """

    return category in PHRASE_CATEGORIES


def get_phrase_category_label(
    category: str,
) -> str:
    """
    Devuelve el nombre legible de una categoría.
    """

    return PHRASE_CATEGORY_LABELS.get(
        category,
        "Categoría desconocida",
    )


# =============================================================================
# BANCO DE FRASES
# =============================================================================

@dataclass(frozen=True)
class PhraseBank:
    """
    Almacena las frases de una identidad.

    Atributos:
        identity_name:
            Nombre interno de la identidad propietaria.

            Ejemplos:

                daxter
                coco

        categories:
            Diccionario cuyas claves son categorías
            y cuyos valores son colecciones de frases.
    """

    identity_name: str

    categories: dict[
        str,
        tuple[str, ...],
    ] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        """
        Valida y normaliza el banco de frases.
        """

        identity_name = (
            self.identity_name
            .strip()
            .casefold()
        )

        if not identity_name:

            raise ValueError(
                "El banco de frases debe pertenecer "
                "a una identidad."
            )

        if not isinstance(
            self.categories,
            dict,
        ):

            raise TypeError(
                "Las categorías deben proporcionarse "
                "mediante un diccionario."
            )

        normalized_categories = {}

        for category, phrases in self.categories.items():

            normalized_category = (
                str(category)
                .strip()
                .casefold()
            )

            if not is_valid_phrase_category(
                normalized_category
            ):

                raise ValueError(
                    "Categoría de frases no válida: "
                    f"{normalized_category}"
                )

            normalized_phrases = (
                self._normalize_phrases(
                    phrases
                )
            )

            normalized_categories[
                normalized_category
            ] = normalized_phrases

        object.__setattr__(
            self,
            "identity_name",
            identity_name,
        )

        object.__setattr__(
            self,
            "categories",
            normalized_categories,
        )

    @staticmethod
    def _normalize_phrases(
        phrases,
    ) -> tuple[str, ...]:
        """
        Limpia frases vacías y elimina duplicados.

        La comparación ignora mayúsculas y minúsculas,
        pero conserva la primera forma escrita.
        """

        normalized_phrases = []

        known_phrases = set()

        for phrase in phrases:

            clean_phrase = str(
                phrase
            ).strip()

            if not clean_phrase:
                continue

            phrase_key = clean_phrase.casefold()

            if phrase_key in known_phrases:
                continue

            known_phrases.add(
                phrase_key
            )

            normalized_phrases.append(
                clean_phrase
            )

        return tuple(
            normalized_phrases
        )

    def has_category(
        self,
        category: str,
    ) -> bool:
        """
        Indica si existe una categoría.
        """

        normalized_category = (
            category
            .strip()
            .casefold()
        )

        return (
            normalized_category
            in self.categories
        )

    def get_phrases(
        self,
        category: str,
    ) -> tuple[str, ...]:
        """
        Devuelve todas las frases de una categoría.

        Si la categoría no está presente, devuelve
        una tupla vacía.
        """

        normalized_category = (
            category
            .strip()
            .casefold()
        )

        if not is_valid_phrase_category(
            normalized_category
        ):

            raise ValueError(
                "Categoría de frases no válida: "
                f"{normalized_category}"
            )

        return self.categories.get(
            normalized_category,
            (),
        )

    def get_random_phrase(
        self,
        category: str,
        default: str | None = None,
        **values,
    ) -> str | None:
        """
        Devuelve una frase aleatoria de una categoría.

        Parámetros:
            category:
                Categoría que debe utilizarse.

            default:
                Texto devuelto si no existen frases.

            **values:
                Valores utilizados para completar
                marcadores dentro de la frase.

        Ejemplo de frase:

            "Modo {mode} activado."

        Ejemplo de llamada:

            get_random_phrase(
                MODE_CHANGED,
                mode="Trabajo",
            )
        """

        phrases = self.get_phrases(
            category
        )

        if not phrases:
            return default

        selected_phrase = random.choice(
            phrases
        )

        if not values:
            return selected_phrase

        try:

            return selected_phrase.format(
                **values
            )

        except (
            KeyError,
            ValueError,
        ):

            # Si falta algún marcador, devolvemos la frase
            # sin modificar para evitar que Atlas falle.
            return selected_phrase

    def count_phrases(
        self,
        category: str | None = None,
    ) -> int:
        """
        Cuenta las frases almacenadas.

        Si se indica una categoría, cuenta únicamente
        las frases de esa categoría.

        Si no se indica, devuelve el total.
        """

        if category is not None:

            return len(
                self.get_phrases(
                    category
                )
            )

        return sum(
            len(phrases)
            for phrases in self.categories.values()
        )

    def list_categories(
        self,
    ) -> list[str]:
        """
        Devuelve las categorías presentes.
        """

        return sorted(
            self.categories.keys()
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte el banco en un diccionario serializable.
        """

        return {
            "identity_name": self.identity_name,
            "categories": {
                category: list(
                    phrases
                )
                for category, phrases
                in self.categories.items()
            },
        }

    def __len__(
        self,
    ) -> int:
        """
        Devuelve el número total de frases.
        """

        return self.count_phrases()

    def __repr__(
        self,
    ) -> str:
        """
        Devuelve una representación técnica.
        """

        return (
            "PhraseBank("
            f"identity_name={self.identity_name!r}, "
            f"categories={len(self.categories)}, "
            f"phrases={self.count_phrases()}"
            ")"
        )