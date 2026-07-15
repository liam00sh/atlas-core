"""
===============================================================================

Proyecto Atlas

Archivo: identity/person_status.py

Descripción:

    Define los distintos estados en los que puede encontrarse una
    persona conocida por Atlas.

    Estos estados representan el grado de relación existente entre
    Daxter y cada persona.

    El estado de una persona puede evolucionar automáticamente con el
    tiempo conforme aumentan las interacciones o bien cambiar mediante
    una confirmación explícita del propietario del sistema.

    Actualmente existen cuatro estados:

        - guest:
            Persona vista por primera vez.

        - known:
            Persona conocida ocasionalmente.

        - regular:
            Persona habitual.

        - user:
            Usuario completo de Atlas.

    Este módulo únicamente define los estados y las funciones
    auxiliares relacionadas.

    No almacena información ni modifica perfiles.

===============================================================================
"""


# =============================================================================
# CONSTANTES
# =============================================================================


# Persona vista por primera vez.
#
# Normalmente todavía no dispone de suficiente información para
# considerarla una persona conocida.

GUEST = "guest"


# Persona conocida por Atlas.
#
# Ya ha mantenido varias conversaciones o visitas, pero todavía no
# utiliza Atlas directamente.

KNOWN = "known"


# Persona habitual.
#
# Forma parte del entorno cercano del propietario o utiliza Atlas con
# frecuencia, aunque todavía no tenga un perfil completo.

REGULAR = "regular"


# Usuario completo de Atlas.
#
# Dispone de un perfil propio, memoria, contexto conversacional y
# permisos independientes.

USER = "user"


# =============================================================================
# COLECCIÓN DE ESTADOS
# =============================================================================


PERSON_STATUSES = {

    GUEST,

    KNOWN,

    REGULAR,

    USER,

}


# =============================================================================
# NOMBRES LEGIBLES
# =============================================================================


STATUS_LABELS = {

    GUEST: "Invitado",

    KNOWN: "Conocido",

    REGULAR: "Habitual",

    USER: "Usuario",

}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================


def is_valid_status(
    status: str,
) -> bool:
    """
    Comprueba si un estado es válido.

    Parámetros:
        status:
            Estado que se desea comprobar.

    Devuelve:
        True:
            El estado existe.

        False:
            El estado no está definido.
    """

    return status in PERSON_STATUSES


def get_status_label(
    status: str,
) -> str:
    """
    Devuelve el nombre legible de un estado.

    Parámetros:
        status:
            Estado interno.

    Devuelve:
        str:
            Nombre descriptivo.

    Si el estado no existe, devuelve "Desconocido".
    """

    return STATUS_LABELS.get(
        status,
        "Desconocido",
    )


def can_promote_to_regular(
    encounter_count: int,
) -> bool:
    """
    Indica si una persona ya podría considerarse habitual.

    Actualmente la decisión únicamente depende del número de
    encuentros registrados.

    En futuras versiones también podrán tenerse en cuenta:

        - Tiempo transcurrido.

        - Duración de las conversaciones.

        - Nivel de confianza.

        - Confirmaciones del propietario.

    Parámetros:
        encounter_count:
            Número de encuentros registrados.

    Devuelve:
        True:
            La persona ya podría ascender a habitual.

        False:
            Todavía no cumple los requisitos.
    """

    return encounter_count >= 5


def can_promote_to_user(
    confirmed: bool,
) -> bool:
    """
    Indica si una persona puede convertirse en usuario completo.

    Actualmente solo es posible mediante una confirmación explícita
    del propietario de Atlas.

    Parámetros:
        confirmed:
            Indica si el propietario ha autorizado la creación del
            perfil.

    Devuelve:
        True:
            Puede convertirse en usuario.

        False:
            Todavía no debe crearse el perfil.
    """

    return confirmed