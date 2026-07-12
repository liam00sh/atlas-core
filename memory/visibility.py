"""
===============================================================================
Proyecto Atlas
Archivo: memory/visibility.py

Descripción:
    Este módulo define todos los niveles de privacidad que pueden tener
    los recuerdos almacenados por Atlas.

    También proporciona:

    - Los nombres legibles de cada nivel.
    - Las palabras que puede escribir el usuario.
    - La conversión entre texto y nivel interno.

Ejemplo:

    Usuario:
        "pareja"

    normalize_visibility()

    devuelve:

        PARTNER

Posteriormente access_control.py utilizará ese valor para decidir
quién puede acceder a la información.

Importante:

    Este archivo NO decide quién puede leer un recuerdo.

    Únicamente define los niveles de privacidad.

    Los permisos reales se comprueban en:

        memory/access_control.py

===============================================================================
"""


# =============================================================================
# CONSTANTES DE VISIBILIDAD
# =============================================================================

# Cada constante representa un nivel interno de privacidad.
#
# Se utilizan en toda la memoria para evitar escribir cadenas
# diferentes en distintos archivos.
#
# Ejemplo:
#
#     visibility = PARTNER
#
# en lugar de:
#
#     visibility = "partner"
#
# Esto reduce errores de escritura y facilita futuras modificaciones.

# Solo puede acceder el propietario del recuerdo.
PRIVATE = "private"

# Puede acceder el propietario y el administrador del sistema.
#
# Actualmente:
#
#     Liam
ADMIN_MANAGED = "admin_managed"

# Puede acceder la pareja autorizada.
PARTNER = "partner"

# Puede acceder la familia autorizada.
FAMILY = "family"

# Personas conocidas o de confianza.
KNOWN = "known"

# Información pública.
#
# Cualquier usuario puede consultarla.
PUBLIC = "public"


# =============================================================================
# NOMBRES MOSTRADOS AL USUARIO
# =============================================================================

# Traduce el nombre interno de cada nivel
# a un texto fácil de entender.
#
# Ejemplo:
#
#     PARTNER
#
# se mostrará como:
#
#     "Pareja autorizada"
VISIBILITY_LABELS = {

    PRIVATE: "Solo el propietario",

    ADMIN_MANAGED: "Propietario y administrador",

    PARTNER: "Pareja autorizada",

    FAMILY: "Familia autorizada",

    KNOWN: "Personas de confianza",

    PUBLIC: "Cualquier persona",

}


# =============================================================================
# PALABRAS ACEPTADAS DEL USUARIO
# =============================================================================

# Este diccionario permite que Atlas entienda distintas formas
# de expresar el mismo nivel de privacidad.
#
# Ejemplos:
#
# Usuario escribe:
#
#     3
#
# o
#
#     pareja
#
# Ambas respuestas se convertirán automáticamente
# en:
#
#     PARTNER
#
# Esto facilita el uso del asistente y evita obligar
# al usuario a memorizar palabras exactas.
VISIBILITY_OPTIONS = {

    # -------------------------------------------------------------------------
    # PRIVADO
    # -------------------------------------------------------------------------
    "1": PRIVATE,

    "privado": PRIVATE,

    "privada": PRIVATE,

    "solo yo": PRIVATE,


    # -------------------------------------------------------------------------
    # ADMINISTRADOR
    # -------------------------------------------------------------------------
    "2": ADMIN_MANAGED,

    "administrador": ADMIN_MANAGED,

    "gestion administrativa": ADMIN_MANAGED,

    "gestión administrativa": ADMIN_MANAGED,


    # -------------------------------------------------------------------------
    # PAREJA
    # -------------------------------------------------------------------------
    "3": PARTNER,

    "pareja": PARTNER,


    # -------------------------------------------------------------------------
    # FAMILIA
    # -------------------------------------------------------------------------
    "4": FAMILY,

    "familia": FAMILY,


    # -------------------------------------------------------------------------
    # PERSONAS DE CONFIANZA
    # -------------------------------------------------------------------------
    "5": KNOWN,

    "confianza": KNOWN,

    "conocidos": KNOWN,


    # -------------------------------------------------------------------------
    # PÚBLICO
    # -------------------------------------------------------------------------
    "6": PUBLIC,

    "publico": PUBLIC,

    "público": PUBLIC,

    "cualquiera": PUBLIC,

}


# =============================================================================
# NORMALIZACIÓN DE LA VISIBILIDAD
# =============================================================================

def normalize_visibility(value: str) -> str | None:
    """
    Convierte el texto escrito por el usuario
    en un nivel interno de privacidad.

    Parámetros
    ----------
    value:
        Texto introducido por el usuario.

    Devuelve
    --------
    str:
        Constante de visibilidad correspondiente.

    None:
        Si el texto no coincide con ninguna opción.

    Ejemplos
    --------

        "1"
            -> PRIVATE

        "pareja"
            -> PARTNER

        "familia"
            -> FAMILY

        "cualquiera"
            -> PUBLIC

        "abcdef"
            -> None
    """

    # Eliminamos espacios innecesarios y convertimos
    # el texto a minúsculas para facilitar la comparación.
    return VISIBILITY_OPTIONS.get(
        value.strip().lower()
    )