"""
===============================================================================
Proyecto Atlas
Archivo: assistant_identity/identity_registry.py

Descripción:
    Registro central de identidades disponibles para Atlas.

    Este módulo mantiene un único catálogo con todas las identidades
    instaladas en el sistema.

    Actualmente existen:

        - Daxter
        - Coco

    El registro permite:

        - Obtener una identidad por nombre.
        - Comprobar si existe.
        - Listarlas.
        - Seleccionar la identidad por defecto.

    Este módulo no decide qué identidad está activa.

    Esa responsabilidad pertenece a IdentityManager.

===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

from assistant_identity.identities.daxter import DAXTER
from assistant_identity.identities.coco import COCO


# =============================================================================
# REGISTRO DE IDENTIDADES
# =============================================================================

IDENTITIES = {
    DAXTER.name: DAXTER,
    COCO.name: COCO,
}


DEFAULT_IDENTITY_NAME = DAXTER.name


# =============================================================================
# FUNCIONES
# =============================================================================

def get_identity(
    identity_name: str,
):
    """
    Devuelve una identidad por su nombre.

    Parámetros:
        identity_name:
            Nombre interno.

    Devuelve:
        AssistantIdentity

    Lanza:
        KeyError si no existe.
    """

    normalized = identity_name.strip().casefold()

    return IDENTITIES[normalized]


def has_identity(
    identity_name: str,
) -> bool:
    """
    Indica si existe una identidad.
    """

    normalized = identity_name.strip().casefold()

    return normalized in IDENTITIES


def get_default_identity():
    """
    Devuelve la identidad por defecto.
    """

    return IDENTITIES[
        DEFAULT_IDENTITY_NAME
    ]


def list_identities():
    """
    Devuelve todas las identidades registradas.

    El orden es alfabético.
    """

    return [
        IDENTITIES[name]
        for name in sorted(
            IDENTITIES
        )
    ]