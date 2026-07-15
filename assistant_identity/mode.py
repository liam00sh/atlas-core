"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/mode.py

Descripción:
    Define la entidad AssistantMode utilizada por el sistema de identidad
    del asistente.

    Un modo modifica temporalmente la forma de comportarse de Daxter
    o Coco sin cambiar su identidad.

    Las identidades disponibles son:

        - Daxter.
        - Coco.

    Los modos disponibles serán:

        - classic:
            Conversación normal.

        - work:
            Precisión y productividad.

        - fun:
            Humor y ocio.

        - empathetic:
            Conversaciones personales y delicadas.

    La identidad y el modo son conceptos diferentes.

    Ejemplos:

        Daxter + classic
        Daxter + work
        Coco + fun
        Coco + empathetic

    AssistantMode no:

        - Decide qué identidad está activa.
        - Cambia el modo automáticamente.
        - Guarda preferencias.
        - Construye el prompt completo.
        - Se comunica con el modelo de IA.

    Es únicamente una representación estructurada de un modo.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from dataclasses import dataclass


# =============================================================================
# CONSTANTES
# =============================================================================

CLASSIC_MODE = "classic"
WORK_MODE = "work"
FUN_MODE = "fun"
EMPATHETIC_MODE = "empathetic"


MODE_NAMES = {
    CLASSIC_MODE,
    WORK_MODE,
    FUN_MODE,
    EMPATHETIC_MODE,
}


MODE_LABELS = {
    CLASSIC_MODE: "Clásico",
    WORK_MODE: "Trabajo",
    FUN_MODE: "Divertido",
    EMPATHETIC_MODE: "Empático",
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def is_valid_mode_name(
    mode_name: str,
) -> bool:
    """
    Indica si un nombre de modo es válido.

    Parámetros:
        mode_name:
            Nombre interno del modo.

    Devuelve:
        True:
            El modo existe.

        False:
            El modo no está definido.
    """

    return mode_name in MODE_NAMES


def get_mode_label(
    mode_name: str,
) -> str:
    """
    Devuelve el nombre legible de un modo.

    Si el modo no existe, devuelve "Desconocido".
    """

    return MODE_LABELS.get(
        mode_name,
        "Desconocido",
    )


# =============================================================================
# ENTIDAD DE MODO
# =============================================================================

@dataclass(frozen=True)
class AssistantMode:
    """
    Representa un modo de comportamiento del asistente.

    Atributos:
        name:
            Nombre interno y único.

        label:
            Nombre legible mostrado al usuario.

        description:
            Explicación breve del objetivo del modo.

        behavior_prompt:
            Reglas de comportamiento que se enviarán al modelo.

        humor_level:
            Nivel orientativo de humor entre 0 y 10.

        formality_level:
            Nivel orientativo de formalidad entre 0 y 10.

        empathy_level:
            Nivel orientativo de empatía entre 0 y 10.

        verbosity_level:
            Nivel orientativo de detalle entre 0 y 10.
    """

    name: str

    label: str

    description: str

    behavior_prompt: str

    humor_level: int = 5

    formality_level: int = 5

    empathy_level: int = 5

    verbosity_level: int = 5

    def __post_init__(
        self,
    ) -> None:
        """
        Valida y normaliza los datos del modo.
        """

        name = self.name.strip().casefold()

        label = self.label.strip()

        description = self.description.strip()

        behavior_prompt = self.behavior_prompt.strip()

        if not name:

            raise ValueError(
                "El modo debe tener un nombre."
            )

        if not is_valid_mode_name(
            name
        ):

            raise ValueError(
                f"Nombre de modo no válido: {name}"
            )

        if not label:

            raise ValueError(
                "El modo debe tener un nombre legible."
            )

        if not description:

            raise ValueError(
                "El modo debe tener una descripción."
            )

        if not behavior_prompt:

            raise ValueError(
                "El modo debe contener reglas de comportamiento."
            )

        numeric_levels = {
            "humor_level": self.humor_level,
            "formality_level": self.formality_level,
            "empathy_level": self.empathy_level,
            "verbosity_level": self.verbosity_level,
        }

        for field_name, field_value in numeric_levels.items():

            if not isinstance(
                field_value,
                int,
            ):

                raise TypeError(
                    f"{field_name} debe ser un número entero."
                )

            if not 0 <= field_value <= 10:

                raise ValueError(
                    f"{field_name} debe estar entre 0 y 10."
                )

        object.__setattr__(
            self,
            "name",
            name,
        )

        object.__setattr__(
            self,
            "label",
            label,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "behavior_prompt",
            behavior_prompt,
        )

    def get_prompt_context(
        self,
    ) -> str:
        """
        Construye el texto del modo para incluirlo en el prompt.
        """

        return "\n".join(
            [
                f"Modo activo: {self.label}",
                f"Objetivo del modo: {self.description}",
                "",
                "Reglas específicas del modo:",
                self.behavior_prompt,
                "",
                (
                    "Nivel orientativo de humor: "
                    f"{self.humor_level}/10"
                ),
                (
                    "Nivel orientativo de formalidad: "
                    f"{self.formality_level}/10"
                ),
                (
                    "Nivel orientativo de empatía: "
                    f"{self.empathy_level}/10"
                ),
                (
                    "Nivel orientativo de detalle: "
                    f"{self.verbosity_level}/10"
                ),
            ]
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte el modo en un diccionario serializable.
        """

        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "behavior_prompt": self.behavior_prompt,
            "humor_level": self.humor_level,
            "formality_level": self.formality_level,
            "empathy_level": self.empathy_level,
            "verbosity_level": self.verbosity_level,
        }