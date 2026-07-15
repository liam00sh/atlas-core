"""
===============================================================================
Proyecto Atlas
Archivo: identity/visitor_manager.py

Descripción:
    Gestiona la evolución social de las personas conocidas por Atlas.

    VisitorManager registra encuentros y analiza si una persona
    podría cambiar de estado dentro de Atlas Identity System.

    Los estados disponibles son:

        guest:
            Invitado o persona vista por primera vez.

        known:
            Persona conocida.

        regular:
            Persona habitual.

        user:
            Usuario completo de Atlas.

    Sus responsabilidades principales son:

    - Registrar encuentros con personas.
    - Consultar el número de encuentros acumulados.
    - Detectar cuándo una persona puede pasar de invitada a conocida.
    - Detectar cuándo una persona puede proponerse como habitual.
    - Mantener pendientes las propuestas de promoción.
    - Confirmar o rechazar promociones.
    - Evitar promociones automáticas importantes.
    - Registrar las decisiones en los logs.

    VisitorManager no:

    - Reconoce voces.
    - Reconoce rostros.
    - Decide que dos nombres corresponden a la misma persona.
    - Crea perfiles completos de usuario.
    - Modifica relaciones familiares.
    - Interpreta conversaciones completas.
    - Cambia automáticamente una persona a estado user.

    La filosofía de este módulo es:

        Daxter observa, aprende y propone.

        El propietario del sistema conserva el control
        sobre las decisiones sociales importantes.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from datetime import datetime

from core.log_manager import info

from identity.people_manager import PeopleManager

from identity.person import Person

from identity.person_status import GUEST
from identity.person_status import KNOWN
from identity.person_status import REGULAR
from identity.person_status import USER

from identity.person_status import can_promote_to_regular


# =============================================================================
# CONSTANTES
# =============================================================================

# Número mínimo de encuentros recomendado para considerar
# que una persona deja de ser una invitada ocasional.
KNOWN_ENCOUNTER_THRESHOLD = 2


# Número mínimo de encuentros recomendado para proponer
# que una persona sea considerada habitual.
REGULAR_ENCOUNTER_THRESHOLD = 5


# Tipos de promoción reconocidos.
PROMOTION_TO_KNOWN = "promote_to_known"
PROMOTION_TO_REGULAR = "promote_to_regular"


VALID_PROMOTION_TYPES = {
    PROMOTION_TO_KNOWN,
    PROMOTION_TO_REGULAR,
}


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class VisitorManager:
    """
    Gestiona encuentros y propuestas de evolución social.

    VisitorManager trabaja sobre PeopleManager y no accede
    directamente a los archivos JSON.
    """

    def __init__(
        self,
        people_manager: PeopleManager,
    ) -> None:
        """
        Inicializa el gestor de visitantes.

        Parámetros:
            people_manager:
                Gestor de personas utilizado para consultar
                y actualizar entidades.
        """

        if not isinstance(
            people_manager,
            PeopleManager,
        ):

            raise TypeError(
                "people_manager debe ser una instancia "
                "de PeopleManager."
            )

        self.people_manager = (
            people_manager
        )

        # Propuestas de promoción todavía no resueltas.
        #
        # Estructura:
        #
        # {
        #     "person-id": {
        #         "person_id": "...",
        #         "promotion_type": "...",
        #         "current_status": "...",
        #         "proposed_status": "...",
        #         "encounter_count": 5,
        #         "created_at": "...",
        #     }
        # }
        self.pending_promotions: dict[
            str,
            dict,
        ] = {}

        info(
            "VisitorManager inicializado."
        )

    # =========================================================================
    # CONSULTA DE PERSONAS
    # =========================================================================

    def get_person(
        self,
        person_id: str,
    ) -> Person | None:
        """
        Devuelve una persona por su identificador.
        """

        return self.people_manager.get_person_by_id(
            person_id
        )

    def get_pending_promotions(
        self,
    ) -> list[dict]:
        """
        Devuelve una copia de todas las promociones pendientes.
        """

        return [
            promotion.copy()
            for promotion in self.pending_promotions.values()
        ]

    def get_pending_promotion(
        self,
        person_id: str,
    ) -> dict | None:
        """
        Devuelve la promoción pendiente de una persona.
        """

        person_key = (
            person_id.strip().casefold()
        )

        if not person_key:
            return None

        promotion = self.pending_promotions.get(
            person_key
        )

        if promotion is None:
            return None

        return promotion.copy()

    def has_pending_promotion(
        self,
        person_id: str,
    ) -> bool:
        """
        Indica si existe una promoción pendiente
        para una persona.
        """

        return (
            self.get_pending_promotion(
                person_id
            )
            is not None
        )

    # =========================================================================
    # REGISTRO DE ENCUENTROS
    # =========================================================================

    def register_visit(
        self,
        person_id: str,
        occurred_at: str | None = None,
    ) -> Person | None:
        """
        Registra una nueva visita o encuentro.

        Después de guardar el encuentro, analiza si debe
        proponerse un cambio de estado.

        Parámetros:
            person_id:
                Identificador de la persona.

            occurred_at:
                Fecha opcional del encuentro.

                Si no se proporciona, se utiliza el momento actual.

        Devuelve:
            Person:
                Persona actualizada.

            None:
                La persona no existe o no pudo guardarse.
        """

        person = (
            self.people_manager.register_person_encounter(
                person_id=person_id,
                occurred_at=occurred_at,
            )
        )

        if person is None:
            return None

        self.evaluate_person_status(
            person.id
        )

        info(
            f"Visita registrada para {person.name}. "
            f"Encuentros: {person.encounter_count}. "
            f"Estado: {person.status}."
        )

        return person

    def register_visit_by_name(
        self,
        name: str,
        occurred_at: str | None = None,
    ) -> Person | None:
        """
        Registra una visita buscando la persona por nombre o alias.
        """

        person = (
            self.people_manager.find_person_by_name(
                name
            )
        )

        if person is None:
            return None

        return self.register_visit(
            person_id=person.id,
            occurred_at=occurred_at,
        )

    # =========================================================================
    # EVALUACIÓN DE ESTADO
    # =========================================================================

    def evaluate_person_status(
        self,
        person_id: str,
    ) -> dict | None:
        """
        Analiza si una persona podría cambiar de estado.

        Reglas actuales:

            guest:
                Puede proponerse como known tras dos encuentros.

            known:
                Puede proponerse como regular tras cinco encuentros.

            regular:
                No asciende automáticamente a user.

            user:
                No necesita promoción social.

        Devuelve:
            dict:
                Propuesta generada o ya existente.

            None:
                No corresponde realizar ninguna propuesta.
        """

        person = self.get_person(
            person_id
        )

        if person is None:
            return None

        # Los usuarios completos no necesitan promoción.
        if person.status == USER:

            self.clear_pending_promotion(
                person.id
            )

            return None

        # Las personas habituales tampoco ascienden
        # automáticamente a usuario.
        if person.status == REGULAR:

            self.clear_pending_promotion(
                person.id
            )

            return None

        if (
            person.status == GUEST
            and person.encounter_count
            >= KNOWN_ENCOUNTER_THRESHOLD
        ):

            return self._create_promotion_proposal(
                person=person,
                promotion_type=(
                    PROMOTION_TO_KNOWN
                ),
                proposed_status=KNOWN,
            )

        if (
            person.status == KNOWN
            and can_promote_to_regular(
                person.encounter_count
            )
        ):

            return self._create_promotion_proposal(
                person=person,
                promotion_type=(
                    PROMOTION_TO_REGULAR
                ),
                proposed_status=REGULAR,
            )

        return None

    def _create_promotion_proposal(
        self,
        *,
        person: Person,
        promotion_type: str,
        proposed_status: str,
    ) -> dict:
        """
        Crea o actualiza una propuesta de promoción.
        """

        if promotion_type not in VALID_PROMOTION_TYPES:

            raise ValueError(
                "Tipo de promoción no válido: "
                f"{promotion_type}"
            )

        person_key = (
            person.id.casefold()
        )

        existing_promotion = (
            self.pending_promotions.get(
                person_key
            )
        )

        if (
            existing_promotion is not None
            and existing_promotion.get(
                "proposed_status"
            )
            == proposed_status
        ):

            # Actualizamos el contador por si ha habido
            # nuevos encuentros desde la propuesta inicial.
            existing_promotion[
                "encounter_count"
            ] = person.encounter_count

            return existing_promotion.copy()

        promotion = {
            "person_id": person.id,
            "person_name": person.name,
            "promotion_type": promotion_type,
            "current_status": person.status,
            "proposed_status": proposed_status,
            "encounter_count": (
                person.encounter_count
            ),
            "created_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
        }

        self.pending_promotions[
            person_key
        ] = promotion

        info(
            f"Promoción social propuesta para "
            f"{person.name}: "
            f"{person.status} -> {proposed_status}."
        )

        return promotion.copy()

    # =========================================================================
    # CONFIRMACIÓN DE PROMOCIONES
    # =========================================================================

    def confirm_promotion(
        self,
        person_id: str,
    ) -> Person | None:
        """
        Confirma una promoción pendiente.

        Devuelve:
            Person:
                Persona actualizada.

            None:
                No existe la persona, no existe una propuesta
                o no pudo guardarse.
        """

        person = self.get_person(
            person_id
        )

        if person is None:
            return None

        promotion = self.get_pending_promotion(
            person.id
        )

        if promotion is None:
            return None

        proposed_status = promotion.get(
            "proposed_status"
        )

        if proposed_status not in {
            KNOWN,
            REGULAR,
        }:

            info(
                "Promoción rechazada por estado no permitido: "
                f"{proposed_status}."
            )

            return None

        person.change_status(
            proposed_status
        )

        saved = self.people_manager.save_person(
            person
        )

        if not saved:
            return None

        self.clear_pending_promotion(
            person.id
        )

        info(
            f"Promoción social confirmada para "
            f"{person.name}: "
            f"{promotion['current_status']} "
            f"-> {proposed_status}."
        )

        return person

    def reject_promotion(
        self,
        person_id: str,
    ) -> bool:
        """
        Rechaza una promoción pendiente.

        La persona conserva su estado actual.
        """

        promotion = self.get_pending_promotion(
            person_id
        )

        if promotion is None:
            return False

        removed = self.clear_pending_promotion(
            person_id
        )

        if removed:

            info(
                f"Promoción social rechazada para "
                f"{promotion['person_name']}."
            )

        return removed

    def clear_pending_promotion(
        self,
        person_id: str,
    ) -> bool:
        """
        Elimina una promoción pendiente.
        """

        person_key = (
            person_id.strip().casefold()
        )

        if not person_key:
            return False

        if person_key not in self.pending_promotions:
            return False

        del self.pending_promotions[
            person_key
        ]

        return True

    def clear_all_pending_promotions(
        self,
    ) -> int:
        """
        Elimina todas las promociones pendientes.

        Devuelve el número de propuestas eliminadas.
        """

        removed_count = len(
            self.pending_promotions
        )

        self.pending_promotions.clear()

        if removed_count > 0:

            info(
                "Promociones sociales pendientes eliminadas: "
                f"{removed_count}."
            )

        return removed_count

    # =========================================================================
    # CREACIÓN Y REGISTRO DE VISITANTES
    # =========================================================================

    def register_new_visitor(
        self,
        name: str,
        *,
        grammatical_gender: str = "unknown",
        introduced_by: str | None = None,
        summary: str = "",
        aliases: list[str] | None = None,
        occurred_at: str | None = None,
    ) -> Person | None:
        """
        Crea una persona invitada y registra su primer encuentro.

        Si ya existe una persona con ese nombre o alias,
        se registra una nueva visita sobre el registro existente.

        Devuelve:
            Person:
                Persona nueva o actualizada.

            None:
                No se pudo crear ni actualizar.
        """

        existing_person = (
            self.people_manager.find_person_by_name(
                name
            )
        )

        if existing_person is not None:

            return self.register_visit(
                person_id=existing_person.id,
                occurred_at=occurred_at,
            )

        person = (
            self.people_manager.create_person(
                name=name,
                aliases=aliases,
                grammatical_gender=(
                    grammatical_gender
                ),
                status=GUEST,
                introduced_by=introduced_by,
                summary=summary,
                register_first_encounter=False,
            )
        )

        if person is None:
            return None

        return self.register_visit(
            person_id=person.id,
            occurred_at=occurred_at,
        )

    # =========================================================================
    # MENSAJES Y DESCRIPCIONES
    # =========================================================================

    def get_promotion_message(
        self,
        person_id: str,
    ) -> str | None:
        """
        Genera un mensaje legible para una promoción pendiente.
        """

        promotion = self.get_pending_promotion(
            person_id
        )

        if promotion is None:
            return None

        person_name = promotion[
            "person_name"
        ]

        encounter_count = promotion[
            "encounter_count"
        ]

        proposed_status = promotion[
            "proposed_status"
        ]

        if proposed_status == KNOWN:

            return (
                f"He hablado con {person_name} "
                f"{encounter_count} veces. "
                "Parece que ya nos conocemos un poco. "
                "¿Quieres que deje de considerarle "
                "una persona invitada?"
            )

        if proposed_status == REGULAR:

            return (
                f"{person_name} ya ha aparecido "
                f"{encounter_count} veces. "
                "Parece una persona habitual de vuestro entorno. "
                "¿Quieres que empiece a tratarle como tal?"
            )

        return (
            f"Existe una propuesta pendiente "
            f"para {person_name}."
        )

    def describe_person_frequency(
        self,
        person_id: str,
    ) -> str | None:
        """
        Devuelve una descripción breve de la frecuencia
        con la que Atlas ha encontrado a una persona.
        """

        person = self.get_person(
            person_id
        )

        if person is None:
            return None

        count = person.encounter_count

        if count == 0:

            return (
                f"Todavía no he registrado ningún "
                f"encuentro con {person.name}."
            )

        if count == 1:

            return (
                f"He hablado con {person.name} "
                "una vez."
            )

        return (
            f"He hablado con {person.name} "
            f"{count} veces."
        )