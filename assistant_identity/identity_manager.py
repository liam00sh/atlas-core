"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/identity_manager.py

Descripción:
    Gestiona la identidad y el modo de comportamiento activos
    del asistente.

    Actualmente Atlas dispone de dos identidades:

        - Daxter:
            Identidad principal y predeterminada.

        - Coco:
            Identidad femenina alternativa.

    Ambas identidades pueden utilizar cuatro modos:

        - classic:
            Conversación normal.

        - work:
            Precisión y productividad.

        - fun:
            Humor y ocio.

        - empathetic:
            Conversaciones personales o delicadas.

    IdentityManager se encarga de:

        - Mantener la identidad activa.
        - Mantener el modo activo.
        - Cambiar manualmente de identidad.
        - Cambiar manualmente de modo.
        - Aplicar sugerencias automáticas de ModeSelector.
        - Evitar cambios automáticos cuando el modo está bloqueado.
        - Guardar preferencias independientes para cada usuario.
        - Restaurar las preferencias al cambiar de usuario.
        - Construir el contexto de personalidad para el prompt.
        - Obtener frases del banco de la identidad activa.

    IdentityManager no:

        - Gestiona personas o visitantes.
        - Comprueba permisos de memoria.
        - Reconoce voces.
        - Genera respuestas mediante IA.
        - Ejecuta herramientas.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import json

from pathlib import Path

from assistant_identity.assistant_identity import AssistantIdentity

from assistant_identity.identity_registry import get_default_identity
from assistant_identity.identity_registry import get_identity
from assistant_identity.identity_registry import has_identity
from assistant_identity.identity_registry import list_identities

from assistant_identity.mode import CLASSIC_MODE
from assistant_identity.mode import MODE_NAMES
from assistant_identity.mode import get_mode_label

from assistant_identity.mode_selector import ModeSelection
from assistant_identity.mode_selector import ModeSelector


# =============================================================================
# CONSTANTES
# =============================================================================

DEFAULT_PREFERENCES_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "preferences.json"
)


DEFAULT_AUTOMATIC_MODE_CONFIDENCE = 0.70


# =============================================================================
# GESTOR
# =============================================================================

class IdentityManager:
    """
    Gestiona la identidad y el modo activos del asistente.

    Las preferencias se almacenan por usuario.

    Ejemplo:

        Liam:
            Identidad: Daxter
            Modo predeterminado: Clásico
            Modo actual: Trabajo
            Cambio automático: activado

        Saray:
            Identidad: Coco
            Modo predeterminado: Clásico
            Modo actual: Clásico
            Cambio automático: activado
    """

    def __init__(
        self,
        preferences_path: str | Path | None = None,
        mode_selector: ModeSelector | None = None,
        automatic_mode_confidence: float = (
            DEFAULT_AUTOMATIC_MODE_CONFIDENCE
        ),
    ) -> None:
        """
        Inicializa el gestor.

        Parámetros:
            preferences_path:
                Ruta del archivo JSON de preferencias.

                Si no se indica, utiliza:

                    assistant_identity/data/preferences.json

            mode_selector:
                Selector utilizado para sugerir modos.

                Si no se proporciona, se crea uno nuevo.

            automatic_mode_confidence:
                Confianza mínima necesaria para aplicar
                automáticamente una sugerencia.
        """

        if preferences_path is None:

            self.preferences_path = (
                DEFAULT_PREFERENCES_PATH
            )

        else:

            self.preferences_path = Path(
                preferences_path
            )

        if (
            mode_selector is not None
            and not isinstance(
                mode_selector,
                ModeSelector,
            )
        ):

            raise TypeError(
                "mode_selector debe ser una instancia "
                "de ModeSelector o None."
            )

        if not isinstance(
            automatic_mode_confidence,
            (
                int,
                float,
            ),
        ):

            raise TypeError(
                "automatic_mode_confidence debe ser numérico."
            )

        automatic_mode_confidence = float(
            automatic_mode_confidence
        )

        if not 0.0 <= automatic_mode_confidence <= 1.0:

            raise ValueError(
                "automatic_mode_confidence debe estar "
                "entre 0.0 y 1.0."
            )

        self.mode_selector = (
            mode_selector
            if mode_selector is not None
            else ModeSelector()
        )

        self.automatic_mode_confidence = (
            automatic_mode_confidence
        )

        # Preferencias completas de todos los usuarios.
        self._preferences: dict[str, dict] = {}

        # Usuario cuyas preferencias están cargadas.
        self._current_user: str | None = None

        # Identidad activa.
        self._active_identity: AssistantIdentity = (
            get_default_identity()
        )

        # Modo activo.
        self._active_mode_name = (
            self._active_identity.default_mode
        )

        # Modo predeterminado del usuario.
        self._default_mode_name = (
            self._active_identity.default_mode
        )

        # Permite cambios automáticos según la situación.
        self._automatic_mode_enabled = True

        # Cuando es True, el usuario ha seleccionado
        # manualmente un modo y el selector automático
        # no debe sustituirlo.
        self._manual_mode_lock = False

        # Indica si el modo actual es un cambio temporal
        # sugerido automáticamente.
        self._temporary_mode_active = False

        self._ensure_preferences_file()

        self._load_preferences()

    # =========================================================================
    # NORMALIZACIÓN
    # =========================================================================

    @staticmethod
    def _normalize_user_key(
        user_name: str,
    ) -> str:
        """
        Normaliza un nombre para utilizarlo como clave interna.
        """

        return user_name.strip().casefold()

    @staticmethod
    def _normalize_mode_name(
        mode_name: str,
    ) -> str:
        """
        Normaliza y valida un nombre de modo.
        """

        normalized_mode_name = (
            mode_name
            .strip()
            .casefold()
        )

        if normalized_mode_name not in MODE_NAMES:

            raise ValueError(
                f"Modo no válido: {normalized_mode_name}"
            )

        return normalized_mode_name

    # =========================================================================
    # ARCHIVO DE PREFERENCIAS
    # =========================================================================

    def _ensure_preferences_file(
        self,
    ) -> None:
        """
        Crea la carpeta y el archivo de preferencias
        si todavía no existen.
        """

        self.preferences_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.preferences_path.exists():
            return

        self.preferences_path.write_text(
            "{}",
            encoding="utf-8",
        )

    def _load_preferences(
        self,
    ) -> None:
        """
        Lee las preferencias desde el archivo JSON.

        Si el archivo está vacío o dañado, se utiliza
        un diccionario vacío para no impedir el arranque.
        """

        try:

            content = self.preferences_path.read_text(
                encoding="utf-8"
            ).strip()

        except OSError:

            self._preferences = {}

            return

        if not content:

            self._preferences = {}

            return

        try:

            loaded_data = json.loads(
                content
            )

        except json.JSONDecodeError:

            self._preferences = {}

            return

        if not isinstance(
            loaded_data,
            dict,
        ):

            self._preferences = {}

            return

        self._preferences = loaded_data

    def _save_preferences(
        self,
    ) -> bool:
        """
        Guarda las preferencias en el archivo JSON.

        Devuelve:
            True:
                Se han guardado correctamente.

            False:
                No ha sido posible escribir el archivo.
        """

        try:

            serialized_data = json.dumps(
                self._preferences,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
            )

            self.preferences_path.write_text(
                serialized_data,
                encoding="utf-8",
            )

        except OSError:

            return False

        return True

    # =========================================================================
    # PREFERENCIAS PREDETERMINADAS
    # =========================================================================

    @staticmethod
    def _build_default_preferences(
    ) -> dict:
        """
        Construye las preferencias iniciales de un usuario.
        """

        default_identity = (
            get_default_identity()
        )

        return {
            "identity": default_identity.name,
            "default_mode": (
                default_identity.default_mode
            ),
            "current_mode": (
                default_identity.default_mode
            ),
            "automatic_mode": True,
            "manual_mode_lock": False,
        }

    def _get_or_create_user_preferences(
        self,
        user_name: str,
    ) -> dict:
        """
        Devuelve las preferencias de un usuario.

        Si no existen, crea las predeterminadas.
        """

        user_key = self._normalize_user_key(
            user_name
        )

        if not user_key:

            raise ValueError(
                "El usuario no puede estar vacío."
            )

        preferences = self._preferences.get(
            user_key
        )

        if not isinstance(
            preferences,
            dict,
        ):

            preferences = (
                self._build_default_preferences()
            )

            self._preferences[
                user_key
            ] = preferences

            self._save_preferences()

        return preferences

    # =========================================================================
    # CARGA DE USUARIO
    # =========================================================================

    def load_user(
        self,
        user_name: str,
    ) -> None:
        """
        Carga la identidad y los modos preferidos
        de un usuario.

        Debe llamarse cuando cambia la persona que habla
        o el usuario activo.
        """

        clean_user_name = user_name.strip()

        if not clean_user_name:

            raise ValueError(
                "El nombre del usuario no puede estar vacío."
            )

        preferences = (
            self._get_or_create_user_preferences(
                clean_user_name
            )
        )

        identity_name = str(
            preferences.get(
                "identity",
                get_default_identity().name,
            )
        ).strip().casefold()

        if not has_identity(
            identity_name
        ):

            identity = get_default_identity()

        else:

            identity = get_identity(
                identity_name
            )

        default_mode_name = str(
            preferences.get(
                "default_mode",
                identity.default_mode,
            )
        ).strip().casefold()

        if not identity.has_mode(
            default_mode_name
        ):

            default_mode_name = (
                identity.default_mode
            )

        current_mode_name = str(
            preferences.get(
                "current_mode",
                default_mode_name,
            )
        ).strip().casefold()

        if not identity.has_mode(
            current_mode_name
        ):

            current_mode_name = (
                default_mode_name
            )

        automatic_mode_enabled = bool(
            preferences.get(
                "automatic_mode",
                True,
            )
        )

        manual_mode_lock = bool(
            preferences.get(
                "manual_mode_lock",
                False,
            )
        )

        self._current_user = (
            self._normalize_user_key(
                clean_user_name
            )
        )

        self._active_identity = identity

        self._default_mode_name = (
            default_mode_name
        )

        self._active_mode_name = (
            current_mode_name
        )

        self._automatic_mode_enabled = (
            automatic_mode_enabled
        )

        self._manual_mode_lock = (
            manual_mode_lock
        )

        self._temporary_mode_active = False

        self._persist_current_state()

    def get_current_user(
        self,
    ) -> str | None:
        """
        Devuelve el usuario cuyas preferencias
        están cargadas actualmente.
        """

        return self._current_user

    # =========================================================================
    # IDENTIDAD ACTIVA
    # =========================================================================

    def get_active_identity(
        self,
    ) -> AssistantIdentity:
        """
        Devuelve la identidad activa.
        """

        return self._active_identity

    def get_active_identity_name(
        self,
    ) -> str:
        """
        Devuelve el nombre interno de la identidad activa.
        """

        return self._active_identity.name

    def get_active_display_name(
        self,
    ) -> str:
        """
        Devuelve el nombre visible de la identidad activa.
        """

        return self._active_identity.display_name

    def change_identity(
        self,
        identity_name: str,
        save_preference: bool = True,
    ) -> bool:
        """
        Cambia la identidad activa y restaura su modo predeterminado.

        Parámetros:
            identity_name:
                Nombre interno, visible o alias.

            save_preference:
                Si es True, guarda la identidad como
                preferencia del usuario actual.

        Devuelve:
            True:
                La identidad ha sido encontrada y activada.

            False:
                No existe ninguna identidad coincidente.
        """

        requested_value = identity_name.strip()

        if not requested_value:
            return False

        selected_identity = None

        for identity in list_identities():

            if identity.matches_name(
                requested_value
            ):

                selected_identity = identity

                break

        if selected_identity is None:
            return False

        self._active_identity = (
            selected_identity
        )

        # Cada identidad comienza en su modo predeterminado.
        #
        # Los modos describen el estado de una identidad concreta;
        # no deben arrastrarse al cambiar entre Daxter y Coco. Por
        # ejemplo, si Daxter estaba en modo Divertido, Coco debe
        # comenzar en su modo Clásico salvo que el usuario solicite
        # expresamente otro modo después del cambio.
        self._default_mode_name = (
            selected_identity.default_mode
        )

        self._active_mode_name = (
            selected_identity.default_mode
        )

        # El cambio de identidad también libera cualquier bloqueo
        # manual o modo temporal heredado de la identidad anterior.
        self._manual_mode_lock = False

        self._temporary_mode_active = False

        if save_preference:

            self._persist_current_state()

        return True

    def reset_identity(
        self,
    ) -> None:
        """
        Restaura la identidad predeterminada.
        """

        default_identity = (
            get_default_identity()
        )

        self._active_identity = (
            default_identity
        )

        self._default_mode_name = (
            default_identity.default_mode
        )

        self._active_mode_name = (
            default_identity.default_mode
        )

        self._manual_mode_lock = False

        self._temporary_mode_active = False

        self._persist_current_state()

    # =========================================================================
    # MODO ACTIVO
    # =========================================================================

    def get_active_mode_name(
        self,
    ) -> str:
        """
        Devuelve el nombre interno del modo activo.
        """

        return self._active_mode_name

    def get_active_mode(
        self,
    ):
        """
        Devuelve el objeto AssistantMode activo.
        """

        mode = self._active_identity.get_mode(
            self._active_mode_name
        )

        if mode is None:

            mode = (
                self._active_identity
                .get_default_mode()
            )

        return mode

    def get_active_mode_label(
        self,
    ) -> str:
        """
        Devuelve el nombre legible del modo activo.
        """

        return get_mode_label(
            self._active_mode_name
        )

    def get_default_mode_name(
        self,
    ) -> str:
        """
        Devuelve el modo predeterminado del usuario.
        """

        return self._default_mode_name

    def set_mode(
        self,
        mode_name: str,
        manual: bool = True,
        temporary: bool = False,
        save_preference: bool = True,
    ) -> bool:
        """
        Activa un modo.

        Parámetros:
            mode_name:
                Nombre interno del modo.

            manual:
                Indica si el cambio fue solicitado
                directamente por el usuario.

                Cuando es True, el modo queda bloqueado
                frente a cambios automáticos.

            temporary:
                Indica si el modo se ha activado
                temporalmente según la situación.

            save_preference:
                Controla si el estado debe guardarse.

        Devuelve:
            True:
                El modo existe y se ha activado.

            False:
                La identidad no dispone de ese modo.
        """

        try:

            normalized_mode_name = (
                self._normalize_mode_name(
                    mode_name
                )
            )

        except ValueError:

            return False

        if not self._active_identity.has_mode(
            normalized_mode_name
        ):

            return False

        self._active_mode_name = (
            normalized_mode_name
        )

        self._manual_mode_lock = bool(
            manual
        )

        self._temporary_mode_active = bool(
            temporary
        )

        if save_preference:

            self._persist_current_state()

        return True

    def set_default_mode(
        self,
        mode_name: str,
    ) -> bool:
        """
        Cambia el modo predeterminado del usuario.

        No activa necesariamente ese modo de inmediato.
        """

        try:

            normalized_mode_name = (
                self._normalize_mode_name(
                    mode_name
                )
            )

        except ValueError:

            return False

        if not self._active_identity.has_mode(
            normalized_mode_name
        ):

            return False

        self._default_mode_name = (
            normalized_mode_name
        )

        self._persist_current_state()

        return True

    def return_to_default_mode(
        self,
    ) -> None:
        """
        Restaura el modo predeterminado y libera
        cualquier bloqueo manual.
        """

        self._active_mode_name = (
            self._default_mode_name
        )

        self._manual_mode_lock = False

        self._temporary_mode_active = False

        self._persist_current_state()

    def unlock_manual_mode(
        self,
    ) -> None:
        """
        Permite nuevamente los cambios automáticos.

        Mantiene el modo actual, pero deja de considerarlo
        bloqueado manualmente.
        """

        self._manual_mode_lock = False

        self._persist_current_state()

    def is_manual_mode_locked(
        self,
    ) -> bool:
        """
        Indica si el usuario ha fijado manualmente el modo.
        """

        return self._manual_mode_lock

    def is_temporary_mode_active(
        self,
    ) -> bool:
        """
        Indica si el modo actual fue aplicado
        automáticamente de manera temporal.
        """

        return self._temporary_mode_active

    # =========================================================================
    # CAMBIO AUTOMÁTICO
    # =========================================================================

    def is_automatic_mode_enabled(
        self,
    ) -> bool:
        """
        Indica si el cambio automático está activado.
        """

        return self._automatic_mode_enabled

    def set_automatic_mode(
        self,
        enabled: bool,
    ) -> None:
        """
        Activa o desactiva el cambio automático.
        """

        self._automatic_mode_enabled = bool(
            enabled
        )

        self._persist_current_state()

    def evaluate_message(
        self,
        text: str,
    ) -> ModeSelection:
        """
        Analiza un mensaje y devuelve la sugerencia
        del selector sin modificar el modo.
        """

        return self.mode_selector.select(
            text
        )

    def apply_automatic_mode(
        self,
        text: str,
    ) -> ModeSelection:
        """
        Analiza un mensaje y aplica el modo sugerido
        cuando se cumplen las condiciones.

        Reglas:

            - El cambio automático debe estar activado.
            - El modo no puede estar bloqueado manualmente.
            - La confianza debe superar el mínimo.
            - La identidad activa debe disponer del modo.

        Siempre devuelve la selección, aunque no se aplique.
        """

        selection = self.evaluate_message(
            text
        )

        if not self._automatic_mode_enabled:
            return selection

        if self._manual_mode_lock:
            return selection

        if (
            selection.confidence
            < self.automatic_mode_confidence
        ):

            return selection

        if not self._active_identity.has_mode(
            selection.mode_name
        ):

            return selection

        self.set_mode(
            mode_name=selection.mode_name,
            manual=False,
            temporary=selection.temporary,
            save_preference=True,
        )

        return selection

    # =========================================================================
    # FRASES
    # =========================================================================

    def get_phrase(
        self,
        category: str,
        default: str | None = None,
        **values,
    ) -> str | None:
        """
        Devuelve una frase aleatoria de la identidad activa.
        """

        return self._active_identity.get_random_phrase(
            category=category,
            default=default,
            **values,
        )

    # =========================================================================
    # CONTEXTO PARA EL PROMPT
    # =========================================================================

    def build_prompt_context(
        self,
    ) -> str:
        """
        Construye el contexto de personalidad que debe
        enviarse al modelo de IA.
        """

        identity_context = (
            self._active_identity
            .get_prompt_context(
                self._active_mode_name
            )
        )

        automatic_state = (
            "activado"
            if self._automatic_mode_enabled
            else "desactivado"
        )

        manual_lock_state = (
            "sí"
            if self._manual_mode_lock
            else "no"
        )

        temporary_state = (
            "sí"
            if self._temporary_mode_active
            else "no"
        )

        return "\n".join(
            [
                identity_context,
                "",
                "ESTADO DEL SISTEMA DE PERSONALIDAD",
                "",
                (
                    "Cambio automático de modo: "
                    f"{automatic_state}"
                ),
                (
                    "Modo bloqueado manualmente: "
                    f"{manual_lock_state}"
                ),
                (
                    "Modo temporal activo: "
                    f"{temporary_state}"
                ),
                "",
                (
                    "La identidad activa define quién es "
                    "el asistente."
                ),
                (
                    "El modo activo modifica únicamente "
                    "su comportamiento temporal."
                ),
                (
                    "No confundas la identidad del asistente "
                    "con la persona que está hablando."
                ),
            ]
        )

    # =========================================================================
    # ESTADO Y PERSISTENCIA
    # =========================================================================

    def get_state(
        self,
    ) -> dict:
        """
        Devuelve un resumen completo del estado actual.
        """

        return {
            "user": self._current_user,
            "identity": (
                self._active_identity.name
            ),
            "identity_display_name": (
                self._active_identity.display_name
            ),
            "default_mode": (
                self._default_mode_name
            ),
            "current_mode": (
                self._active_mode_name
            ),
            "current_mode_label": (
                self.get_active_mode_label()
            ),
            "automatic_mode": (
                self._automatic_mode_enabled
            ),
            "manual_mode_lock": (
                self._manual_mode_lock
            ),
            "temporary_mode": (
                self._temporary_mode_active
            ),
        }

    def _persist_current_state(
        self,
    ) -> bool:
        """
        Guarda el estado del usuario actual.

        Si todavía no hay usuario cargado, no escribe nada.
        """

        if self._current_user is None:
            return False

        user_key = self._normalize_user_key(
            self._current_user
        )

        self._preferences[
            user_key
        ] = {
            "identity": (
                self._active_identity.name
            ),
            "default_mode": (
                self._default_mode_name
            ),
            "current_mode": (
                self._active_mode_name
            ),
            "automatic_mode": (
                self._automatic_mode_enabled
            ),
            "manual_mode_lock": (
                self._manual_mode_lock
            ),
        }

        return self._save_preferences()

    def reload_preferences(
        self,
    ) -> None:
        """
        Recarga el archivo de preferencias.

        Si existe un usuario activo, vuelve a cargar
        también su configuración.
        """

        current_user = self._current_user

        self._load_preferences()

        if current_user is not None:

            self.load_user(
                current_user
            )

    def reset_user_preferences(
        self,
        user_name: str,
    ) -> bool:
        """
        Elimina las preferencias personalizadas de un usuario.

        La próxima vez se utilizarán los valores predeterminados.
        """

        user_key = self._normalize_user_key(
            user_name
        )

        if user_key not in self._preferences:
            return False

        del self._preferences[
            user_key
        ]

        saved = self._save_preferences()

        if (
            self._current_user is not None
            and self._normalize_user_key(
                self._current_user
            )
            == user_key
        ):

            self.load_user(
                self._current_user
            )

        return saved