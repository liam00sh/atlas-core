"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/assistant_identity.py

Descripción:
    Define la entidad AssistantIdentity utilizada por el sistema
    de identidad del asistente.

    Una identidad representa la personalidad principal con la que
    Atlas se presenta e interactúa con el usuario.

    Actualmente existirán dos identidades:

        - Daxter:
            Identidad principal y predeterminada.

        - Coco:
            Identidad femenina alternativa.

    La identidad y el modo son conceptos diferentes.

    La identidad define:

        - Quién es el asistente.
        - Cómo se llama.
        - Su género gramatical.
        - Su personalidad base.
        - Su estilo de comunicación.
        - Sus saludos y despedidas.
        - Su futura voz.
        - Su futuro avatar.
        - Cómo interpreta cada uno de los modos disponibles.

    El modo modifica temporalmente el comportamiento de una identidad.

    Ejemplos:

        Daxter + classic
        Daxter + work
        Daxter + fun
        Daxter + empathetic

        Coco + classic
        Coco + work
        Coco + fun
        Coco + empathetic

    AssistantIdentity no:

        - Decide qué identidad está activa.
        - Guarda preferencias de usuario.
        - Selecciona automáticamente un modo.
        - Se comunica directamente con el modelo de IA.
        - Ejecuta herramientas.
        - Gestiona personas o permisos.

    Es únicamente una representación estructurada de una identidad.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from dataclasses import dataclass
from dataclasses import field

from assistant_identity.mode import AssistantMode
from assistant_identity.mode import CLASSIC_MODE
from assistant_identity.mode import MODE_NAMES
from assistant_identity.phrase_bank import PhraseBank


# =============================================================================
# CONSTANTES
# =============================================================================

DAXTER_IDENTITY = "daxter"
COCO_IDENTITY = "coco"


IDENTITY_NAMES = {
    DAXTER_IDENTITY,
    COCO_IDENTITY,
}


VALID_GRAMMATICAL_GENDERS = {
    "masculine",
    "feminine",
    "neutral",
    "unknown",
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def is_valid_identity_name(
    identity_name: str,
) -> bool:
    """
    Indica si un nombre de identidad es válido.

    Parámetros:
        identity_name:
            Nombre interno de la identidad.

    Devuelve:
        True:
            La identidad está admitida.

        False:
            La identidad no está definida.
    """

    return identity_name in IDENTITY_NAMES


# =============================================================================
# ENTIDAD DE IDENTIDAD
# =============================================================================

@dataclass(frozen=True)
class AssistantIdentity:
    """
    Representa una identidad disponible dentro de Atlas.

    Atributos:
        name:
            Nombre interno y único.

            Ejemplos:

                daxter
                coco

        display_name:
            Nombre visible de la identidad.

            Ejemplos:

                Daxter
                Coco

        grammatical_gender:
            Género gramatical utilizado al hablar sobre
            la propia identidad.

            Valores admitidos:

                masculine
                feminine
                neutral
                unknown

        description:
            Descripción breve y general de la identidad.

        base_personality_prompt:
            Reglas principales de personalidad que se enviarán
            al modelo de IA.

        default_mode:
            Nombre del modo predeterminado.

            Normalmente:

                classic

        modes:
            Diccionario de modos disponibles para esta identidad.

            Cada identidad puede interpretar los mismos modos
            de una forma diferente.

        greetings:
            Posibles saludos propios de la identidad.

        farewells:
            Posibles despedidas propias de la identidad.

        aliases:
            Otros nombres o formas válidas de identificarla.

        voice_id:
            Identificador reservado para una futura voz.

        avatar_id:
            Identificador reservado para un futuro avatar.
    """

    name: str

    display_name: str

    grammatical_gender: str

    description: str

    base_personality_prompt: str

    modes: dict[str, AssistantMode]

    phrase_bank: PhraseBank | None = None

    default_mode: str = CLASSIC_MODE

    greetings: tuple[str, ...] = field(
        default_factory=tuple
    )

    farewells: tuple[str, ...] = field(
        default_factory=tuple
    )

    aliases: tuple[str, ...] = field(
        default_factory=tuple
    )

    voice_id: str | None = None

    avatar_id: str | None = None

    def __post_init__(
        self,
    ) -> None:
        """
        Valida y normaliza los datos después de crear
        la identidad.
        """

        name = self.name.strip().casefold()

        display_name = self.display_name.strip()

        grammatical_gender = (
            self.grammatical_gender
            .strip()
            .casefold()
        )

        description = self.description.strip()

        base_personality_prompt = (
            self.base_personality_prompt.strip()
        )

        default_mode = (
            self.default_mode
            .strip()
            .casefold()
        )

        if not name:

            raise ValueError(
                "La identidad debe tener un nombre."
            )

        if not is_valid_identity_name(
            name
        ):

            raise ValueError(
                f"Nombre de identidad no válido: {name}"
            )

        if not display_name:

            raise ValueError(
                "La identidad debe tener un nombre visible."
            )

        if (
            grammatical_gender
            not in VALID_GRAMMATICAL_GENDERS
        ):

            raise ValueError(
                "Género gramatical no válido: "
                f"{grammatical_gender}"
            )

        if not description:

            raise ValueError(
                "La identidad debe tener una descripción."
            )

        if not base_personality_prompt:

            raise ValueError(
                "La identidad debe tener una personalidad base."
            )

        if not isinstance(
            self.modes,
            dict,
        ):

            raise TypeError(
                "Los modos deben proporcionarse "
                "mediante un diccionario."
            )

        if not self.modes:

            raise ValueError(
                "La identidad debe disponer de al menos un modo."
            )

        normalized_modes = {}

        for mode_name, mode in self.modes.items():

            if not isinstance(
                mode,
                AssistantMode,
            ):

                raise TypeError(
                    "Todos los modos deben ser objetos "
                    "AssistantMode."
                )

            normalized_mode_name = (
                str(mode_name)
                .strip()
                .casefold()
            )

            if (
                normalized_mode_name
                != mode.name
            ):

                raise ValueError(
                    "La clave del modo debe coincidir "
                    "con el nombre interno del objeto."
                )

            if (
                normalized_mode_name
                not in MODE_NAMES
            ):

                raise ValueError(
                    "Modo no válido para la identidad: "
                    f"{normalized_mode_name}"
                )

            normalized_modes[
                normalized_mode_name
            ] = mode

        if default_mode not in normalized_modes:

            raise ValueError(
                "El modo predeterminado no está disponible "
                f"para la identidad: {default_mode}"
            )

        if (
            self.phrase_bank is not None
            and not isinstance(
                self.phrase_bank,
                PhraseBank,
            )
        ):

            raise TypeError(
                "phrase_bank debe ser un objeto PhraseBank "
                "o None."
            )

        if (
            self.phrase_bank is not None
            and self.phrase_bank.identity_name != name
        ):

            raise ValueError(
                "El banco de frases debe pertenecer "
                "a la misma identidad."
            )

        normalized_greetings = (
            self._normalize_text_collection(
                self.greetings
            )
        )

        normalized_farewells = (
            self._normalize_text_collection(
                self.farewells
            )
        )

        normalized_aliases = (
            self._normalize_aliases(
                aliases=self.aliases,
                display_name=display_name,
                internal_name=name,
            )
        )

        normalized_voice_id = (
            self._normalize_optional_text(
                self.voice_id
            )
        )

        normalized_avatar_id = (
            self._normalize_optional_text(
                self.avatar_id
            )
        )

        object.__setattr__(
            self,
            "name",
            name,
        )

        object.__setattr__(
            self,
            "display_name",
            display_name,
        )

        object.__setattr__(
            self,
            "grammatical_gender",
            grammatical_gender,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "base_personality_prompt",
            base_personality_prompt,
        )

        object.__setattr__(
            self,
            "modes",
            normalized_modes,
        )

        object.__setattr__(
            self,
            "default_mode",
            default_mode,
        )

        object.__setattr__(
            self,
            "greetings",
            normalized_greetings,
        )

        object.__setattr__(
            self,
            "farewells",
            normalized_farewells,
        )

        object.__setattr__(
            self,
            "aliases",
            normalized_aliases,
        )

        object.__setattr__(
            self,
            "voice_id",
            normalized_voice_id,
        )

        object.__setattr__(
            self,
            "avatar_id",
            normalized_avatar_id,
        )

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        """
        Normaliza un texto opcional.

        Devuelve None si el valor está vacío.
        """

        if value is None:
            return None

        normalized_value = str(
            value
        ).strip()

        return normalized_value or None

    @staticmethod
    def _normalize_text_collection(
        values,
    ) -> tuple[str, ...]:
        """
        Limpia una colección de textos y elimina duplicados.

        La comparación ignora mayúsculas y minúsculas,
        pero conserva la primera forma escrita.
        """

        normalized_values = []

        known_values = set()

        for value in values:

            clean_value = str(
                value
            ).strip()

            if not clean_value:
                continue

            value_key = clean_value.casefold()

            if value_key in known_values:
                continue

            known_values.add(
                value_key
            )

            normalized_values.append(
                clean_value
            )

        return tuple(
            normalized_values
        )

    @classmethod
    def _normalize_aliases(
        cls,
        aliases,
        display_name: str,
        internal_name: str,
    ) -> tuple[str, ...]:
        """
        Normaliza los alias de una identidad.

        No permite alias duplicados ni alias idénticos
        al nombre visible o al nombre interno.
        """

        normalized_aliases = (
            cls._normalize_text_collection(
                aliases
            )
        )

        excluded_names = {
            display_name.casefold(),
            internal_name.casefold(),
        }

        return tuple(
            alias
            for alias in normalized_aliases
            if alias.casefold()
            not in excluded_names
        )

    def get_mode(
        self,
        mode_name: str,
    ) -> AssistantMode | None:
        """
        Devuelve uno de los modos de la identidad.

        Parámetros:
            mode_name:
                Nombre interno del modo.

        Devuelve:
            AssistantMode:
                Modo encontrado.

            None:
                La identidad no dispone de ese modo.
        """

        normalized_mode_name = (
            mode_name
            .strip()
            .casefold()
        )

        return self.modes.get(
            normalized_mode_name
        )

    def get_default_mode(
        self,
    ) -> AssistantMode:
        """
        Devuelve el modo predeterminado.

        La validación realizada durante la creación de la
        identidad garantiza que siempre existe.
        """

        return self.modes[
            self.default_mode
        ]

    def has_mode(
        self,
        mode_name: str,
    ) -> bool:
        """
        Indica si la identidad dispone de un modo.
        """

        return (
            self.get_mode(
                mode_name
            )
            is not None
        )

    def matches_name(
        self,
        value: str,
    ) -> bool:
        """
        Comprueba si un texto identifica a esta identidad.

        La comparación incluye:

        - Nombre interno.
        - Nombre visible.
        - Alias.

        Ignora mayúsculas y minúsculas.
        """

        normalized_value = (
            value
            .strip()
            .casefold()
        )

        if not normalized_value:
            return False

        if normalized_value in {
            self.name,
            self.display_name.casefold(),
        }:

            return True

        return any(
            alias.casefold()
            == normalized_value
            for alias in self.aliases
        )

    def get_random_phrase(
        self,
        category: str,
        default: str | None = None,
        **values,
    ) -> str | None:
        """
        Devuelve una frase aleatoria de la identidad.

        Si la identidad no dispone de banco de frases,
        devuelve el valor predeterminado.
        """

        if self.phrase_bank is None:
            return default

        return self.phrase_bank.get_random_phrase(
            category=category,
            default=default,
            **values,
        )

    def get_prompt_context(
        self,
        mode_name: str | None = None,
    ) -> str:
        """
        Construye el contexto completo de la identidad
        y el modo activo.

        Parámetros:
            mode_name:
                Nombre del modo que debe aplicarse.

                Si no se proporciona, utiliza el modo
                predeterminado.

        Devuelve:
            str:
                Texto preparado para incluirlo en el prompt.
        """

        resolved_mode_name = (
            mode_name
            if mode_name is not None
            else self.default_mode
        )

        mode = self.get_mode(
            resolved_mode_name
        )

        if mode is None:

            raise ValueError(
                f"La identidad {self.display_name} "
                f"no dispone del modo "
                f"{resolved_mode_name}."
            )

        return "\n".join(
            [
                "IDENTIDAD DEL ASISTENTE",
                "",
                (
                    "Nombre de la identidad activa: "
                    f"{self.display_name}"
                ),
                (
                    "Género gramatical de la identidad: "
                    f"{self.grammatical_gender}"
                ),
                (
                    "Descripción general: "
                    f"{self.description}"
                ),
                "",
                "Personalidad base:",
                self.base_personality_prompt,
                "",
                mode.get_prompt_context(),
                "",
                (
                    "La identidad debe mantenerse durante "
                    "toda la respuesta."
                ),
                (
                    "El modo modifica el comportamiento, "
                    "pero no sustituye la personalidad base."
                ),
            ]
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte la identidad en un diccionario serializable.
        """

        return {
            "name": self.name,
            "display_name": self.display_name,
            "grammatical_gender": (
                self.grammatical_gender
            ),
            "description": self.description,
            "base_personality_prompt": (
                self.base_personality_prompt
            ),
            "default_mode": self.default_mode,
            "modes": {
                mode_name: mode.to_dict()
                for mode_name, mode
                in self.modes.items()
            },
            "phrase_bank": (
                None
                if self.phrase_bank is None
                else self.phrase_bank.to_dict()
            ),
            "greetings": list(
                self.greetings
            ),
            "farewells": list(
                self.farewells
            ),
            "aliases": list(
                self.aliases
            ),
            "voice_id": self.voice_id,
            "avatar_id": self.avatar_id,
        }

    def __str__(
        self,
    ) -> str:
        """
        Devuelve una representación legible.
        """

        return (
            f"{self.display_name} "
            f"({self.default_mode})"
        )

    def __repr__(
        self,
    ) -> str:
        """
        Devuelve una representación técnica.
        """

        return (
            "AssistantIdentity("
            f"name={self.name!r}, "
            f"display_name={self.display_name!r}, "
            f"default_mode={self.default_mode!r}"
            ")"
        )