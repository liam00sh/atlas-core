"""
===============================================================================
Proyecto Atlas
Archivo: memory/classifier.py

Descripción:
    Este módulo intenta decidir automáticamente el nivel de privacidad
    de un recuerdo antes de guardarlo.

    Gracias a este clasificador, Atlas puede reconocer determinados tipos
    de información y proponer una visibilidad adecuada sin necesidad de
    preguntar siempre al usuario.

    Si el sistema no tiene suficiente información para decidir,
    devuelve None y Atlas solicita confirmación.

Ejemplo:

    Usuario:
        Recuerda que mi DNI es 12345678A

    Resultado:

        ADMIN_MANAGED

    ----------------------------

    Usuario:
        Recuerda que solo quiero saber esto yo

    Resultado:

        PRIVATE

    ----------------------------

    Usuario:
        Recuerda que me gusta el chocolate

    Resultado:

        None

    En este caso Atlas preguntará:

        ¿Quién debería poder conocer esta información?

Este módulo representa el primer paso hacia una clasificación automática
de recuerdos basada en reglas.
===============================================================================
"""


# =============================================================================
# IMPORTACIÓN DE LOS NIVELES DE VISIBILIDAD
# =============================================================================

# Importamos todas las categorías posibles para poder devolverlas
# cuando el clasificador detecte determinado tipo de información.

from memory.visibility import ADMIN_MANAGED
from memory.visibility import FAMILY
from memory.visibility import KNOWN
from memory.visibility import PARTNER
from memory.visibility import PRIVATE
from memory.visibility import PUBLIC


# =============================================================================
# PALABRAS CLAVE DE INFORMACIÓN MUY PRIVADA
# =============================================================================

"""
Si cualquiera de estas expresiones aparece dentro del recuerdo,
Atlas asumirá que únicamente debería poder leerlo el propietario.

En el futuro este listado crecerá considerablemente.
"""

HIGHLY_PRIVATE_KEYWORDS = {

    "conversación íntima",
    "conversacion intima",
    "secreto personal",
    "diario personal",
    "solo quiero saberlo yo",

}


# =============================================================================
# PALABRAS CLAVE DE INFORMACIÓN ADMINISTRADA POR LIAM
# =============================================================================

"""
Estos datos suelen corresponder a documentos oficiales o información
que Liam suele gestionar dentro de la familia.

Por ejemplo:

- DNI
- contratos
- seguros
- documentación laboral

Actualmente Atlas los clasifica automáticamente como
ADMIN_MANAGED.
"""

ADMIN_MANAGED_KEYWORDS = {

    "dni",

    "nie",

    "pasaporte",

    "currículum",
    "curriculum",

    "contrato",

    "seguro",

    "póliza",
    "poliza",

    "documentación laboral",
    "documentacion laboral",

    "vida laboral",

    "declaración de la renta",
    "declaracion de la renta",

}


# =============================================================================
# CLASIFICADOR PRINCIPAL
# =============================================================================

def classify_visibility(
    content: str,
) -> tuple[str | None, str]:

    """
    Intenta decidir automáticamente el nivel de privacidad
    de un recuerdo.

    Parámetros
    ----------
    content:
        Texto que el usuario quiere guardar.

    Devuelve
    --------
    tuple:

        (
            visibilidad,
            explicación
        )

    Donde:

        visibilidad

            Puede ser:

                PRIVATE
                ADMIN_MANAGED
                PARTNER
                FAMILY
                KNOWN
                PUBLIC

            o None cuando no existe suficiente información.

        explicación

            Pequeña descripción del motivo por el que se
            ha elegido esa categoría.

    Ejemplo:

        Entrada:

            "Mi DNI es..."

        Salida:

            (
                ADMIN_MANAGED,
                "Parece documentación gestionada por el administrador."
            )
    """

    # Convertimos todo el texto a minúsculas para facilitar
    # las comparaciones.
    normalized_content = content.lower()


    # -------------------------------------------------------------------------
    # INFORMACIÓN MUY PRIVADA
    # -------------------------------------------------------------------------

    # Si aparece cualquiera de las expresiones definidas
    # en HIGHLY_PRIVATE_KEYWORDS,
    # devolvemos PRIVATE.

    if any(

        keyword in normalized_content

        for keyword in HIGHLY_PRIVATE_KEYWORDS

    ):

        return (

            PRIVATE,

            "Parece información personal especialmente privada.",

        )


    # -------------------------------------------------------------------------
    # DOCUMENTACIÓN ADMINISTRATIVA
    # -------------------------------------------------------------------------

    # Si el texto contiene palabras relacionadas con
    # documentos oficiales,
    # Atlas propone ADMIN_MANAGED.

    if any(

        keyword in normalized_content

        for keyword in ADMIN_MANAGED_KEYWORDS

    ):

        return (

            ADMIN_MANAGED,

            "Parece documentación gestionada por el administrador.",

        )


    # -------------------------------------------------------------------------
    # INFORMACIÓN PARA LA PAREJA
    # -------------------------------------------------------------------------

    if "solo mi pareja" in normalized_content:

        return (

            PARTNER,

            "Se ha indicado acceso para la pareja.",

        )


    # -------------------------------------------------------------------------
    # INFORMACIÓN FAMILIAR
    # -------------------------------------------------------------------------

    if "mi familia puede saberlo" in normalized_content:

        return (

            FAMILY,

            "Se ha indicado acceso para la familia.",

        )


    # -------------------------------------------------------------------------
    # PERSONAS DE CONFIANZA
    # -------------------------------------------------------------------------

    if "gente de confianza" in normalized_content:

        return (

            KNOWN,

            "Se ha indicado acceso para personas de confianza.",

        )


    # -------------------------------------------------------------------------
    # INFORMACIÓN PÚBLICA
    # -------------------------------------------------------------------------

    if "lo puede saber cualquiera" in normalized_content:

        return (

            PUBLIC,

            "Se ha indicado acceso público.",

        )


    # -------------------------------------------------------------------------
    # NO EXISTE SUFICIENTE INFORMACIÓN
    # -------------------------------------------------------------------------

    """
    Si ninguna regla coincide,
    Atlas no intenta adivinar.

    Devuelve:

        None

    para que posteriormente Atlas pregunte al usuario
    quién debería poder acceder a ese recuerdo.

    Este comportamiento evita clasificaciones incorrectas.
    """

    return (

        None,

        "No existe suficiente información para clasificarlo.",

    )