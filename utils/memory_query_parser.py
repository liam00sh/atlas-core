"""
===============================================================================
Proyecto Atlas
Archivo: utils/memory_query_parser.py

Descripción:
    Este módulo analiza preguntas relacionadas con la memoria de Atlas.

    Su objetivo es detectar consultas como:

        - "qué sabes de mí"
        - "qué recuerdas de Saray"
        - "mis recuerdos"

    También admite errores frecuentes de escritura:

        - "qeu sabea d saray"
        - "que recuerads de Ruben"
        - "que sabbes de mi"

    A diferencia de text_normalizer.py, este módulo es deliberadamente
    prudente con los nombres propios.

    Corrige las palabras que forman la estructura de la consulta:

        - qué
        - sabes
        - recuerdas
        - de
        - mí

    Pero no intenta corregir automáticamente el nombre consultado.

    Ejemplo:

        "que sabes de sary"

    devolverá el nombre:

        "sary"

    Después UserManager decidirá si existe realmente un usuario
    con ese nombre.

Resultados posibles:

    Consulta sobre el usuario activo:

        {
            "type": "self"
        }

    Consulta sobre otra persona:

        {
            "type": "other",
            "owner": "saray"
        }

    Consulta no reconocida:

        None

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# re permite trabajar con expresiones regulares.
#
# En este archivo se utiliza para:
#
# - Eliminar signos de puntuación.
# - Reducir varios espacios consecutivos a uno solo.
import re

# unicodedata permite analizar caracteres Unicode.
#
# Se utiliza para eliminar acentos sin modificar
# las letras originales.
#
# Ejemplo:
#
#     "qué" -> "que"
#     "Rubén" -> "Ruben"
import unicodedata


# SequenceMatcher compara dos secuencias de caracteres
# y calcula cuánto se parecen.
#
# Devuelve un valor entre:
#
#     0.0 -> completamente diferentes.
#     1.0 -> exactamente iguales.
#
# Se utiliza para reconocer errores de teclado como:
#
#     sabes
#     sabea
#     saves
#     sanes
#     sabbes
from difflib import SequenceMatcher


# =============================================================================
# SUSTITUCIONES DIRECTAS
# =============================================================================

# Diccionario con variantes muy frecuentes de determinadas palabras.
#
# Estas sustituciones se aplican antes de utilizar
# la comparación aproximada.
WORD_REPLACEMENTS = {

    # -------------------------------------------------------------------------
    # VARIANTES FRECUENTES DE "QUE"
    # -------------------------------------------------------------------------
    "qeu": "que",

    "qe": "que",

    "q": "que",

    "ke": "que",


    # -------------------------------------------------------------------------
    # ABREVIATURA O ERROR FRECUENTE DE "DE"
    # -------------------------------------------------------------------------
    "d": "de",


    # -------------------------------------------------------------------------
    # VARIANTE CON ACENTO DE "MI"
    #
    # Normalmente remove_accents() ya convertirá "mí" en "mi",
    # pero se conserva como protección adicional.
    # -------------------------------------------------------------------------
    "mí": "mi",

}


def remove_accents(
    text: str,
) -> str:
    """
    Elimina los acentos de un texto.

    Parámetros:
        text:
            Texto original.

    Devuelve:
        str:
            Texto sin signos diacríticos.

    Ejemplos:
        "qué"   -> "que"
        "Rubén" -> "Ruben"

    No convierte el texto a minúsculas ni elimina signos.
    Únicamente elimina los acentos.
    """

    # NFD separa una letra acentuada en dos elementos.
    #
    # Ejemplo:
    #
    #     "é"
    #
    # se convierte internamente en:
    #
    #     "e" + marca de acento
    normalized = unicodedata.normalize(
        "NFD",
        text,
    )

    # Reconstruimos el texto descartando los caracteres
    # cuya categoría Unicode sea "Mn".
    #
    # "Mn" significa:
    #
    #     Mark, Nonspacing
    #
    # es decir, marcas que no ocupan espacio,
    # como los acentos.
    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        ) != "Mn"
    )


def normalize_basic_text(
    text: str,
) -> str:
    """
    Realiza una normalización básica de la consulta.

    Parámetros:
        text:
            Frase original escrita por el usuario.

    Devuelve:
        str:
            Frase normalizada.

    Operaciones realizadas:

        1. Eliminar espacios exteriores.
        2. Convertir a minúsculas.
        3. Eliminar acentos.
        4. Sustituir signos por espacios.
        5. Reducir espacios duplicados.
        6. Aplicar sustituciones directas.

    Importante:
        No intenta corregir automáticamente los nombres.

    Ejemplo:
        "¿QEU sabes d Saray?"
            -> "que sabes de saray"
    """

    # Eliminamos espacios exteriores, convertimos a minúsculas
    # y eliminamos los acentos.
    text = remove_accents(
        text.strip().lower()
    )

    # Sustituimos cualquier signo de puntuación por un espacio.
    #
    # [^\w\s]
    #
    # significa:
    #
    # - Todo lo que no sea letra, número, guion bajo o espacio.
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    # Sustituimos uno o más espacios consecutivos
    # por un único espacio.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # Separamos la frase en palabras y aplicamos
    # las sustituciones directas.
    #
    # WORD_REPLACEMENTS.get(word, word) significa:
    #
    # - Si existe una corrección, utiliza la corrección.
    # - Si no existe, conserva la palabra original.
    words = [
        WORD_REPLACEMENTS.get(
            word,
            word,
        )
        for word in text.split()
    ]

    # Reconstruimos la frase utilizando un espacio
    # entre cada palabra.
    return " ".join(
        words
    )


def words_are_similar(
    received: str,
    expected: str,
    cutoff: float = 0.72,
) -> bool:
    """
    Comprueba si dos palabras son suficientemente parecidas.

    Parámetros:
        received:
            Palabra recibida del usuario.

        expected:
            Palabra correcta esperada.

        cutoff:
            Similitud mínima necesaria.

            Por defecto:
                0.72, aproximadamente un 72 %.

    Devuelve:
        True:
            Las palabras son suficientemente parecidas.

        False:
            Las palabras no alcanzan el umbral.

    Ejemplos aproximados:
        "sabea" y "sabes" -> True
        "saves" y "sabes" -> True
        "sanes" y "sabes" -> True
        "coche" y "sabes" -> False
    """

    # Aplicamos primero las sustituciones directas
    # a la palabra recibida.
    received = WORD_REPLACEMENTS.get(
        received,
        received,
    )

    # Aplicamos también las sustituciones a la palabra esperada.
    #
    # Normalmente la palabra esperada ya será correcta,
    # pero esto mantiene la función simétrica.
    expected = WORD_REPLACEMENTS.get(
        expected,
        expected,
    )

    # Si las palabras ya son exactamente iguales,
    # no es necesario calcular la similitud.
    if received == expected:
        return True

    # SequenceMatcher compara los caracteres de ambas palabras.
    #
    # El primer parámetro se deja en None porque no necesitamos
    # una función especial para ignorar caracteres.
    similarity = SequenceMatcher(
        None,
        received,
        expected,
    ).ratio()

    # La comparación devuelve True si la similitud
    # alcanza o supera el umbral establecido.
    return similarity >= cutoff


def is_knowledge_verb(
    word: str,
) -> bool:
    """
    Comprueba si una palabra se parece a un verbo utilizado
    para consultar la memoria.

    Actualmente reconoce variantes aproximadas de:

        - sabes
        - recuerdas

    Parámetros:
        word:
            Palabra recibida.

    Devuelve:
        True:
            Se parece suficientemente a "sabes"
            o a "recuerdas".

        False:
            No coincide con ninguno.

    Ejemplos:
        "sabea"      -> True
        "sabbes"     -> True
        "recuerads"  -> True
        "correr"     -> False
    """

    return (

        # Primera posibilidad:
        # la palabra se parece a "sabes".
        words_are_similar(
            word,
            "sabes",
            cutoff=0.70,
        )

        or

        # Segunda posibilidad:
        # la palabra se parece a "recuerdas".
        words_are_similar(
            word,
            "recuerdas",
            cutoff=0.72,
        )

    )


def parse_memory_query(
    text: str,
) -> dict | None:
    """
    Interpreta una consulta relacionada con la memoria.

    Parámetros:
        text:
            Texto original escrito por el usuario.

    Devuelve:
        dict:
            Si reconoce la consulta.

        None:
            Si la frase no sigue una estructura reconocible.

    Posibles diccionarios devueltos:

        Consulta sobre el usuario activo:

            {
                "type": "self"
            }

        Consulta sobre otra persona:

            {
                "type": "other",
                "owner": "saray"
            }

    Ejemplos reconocidos:

        "mis recuerdos"

        "que sabes de mi"

        "qeu sabea d saray"

        "que recuerads de Ruben"
    """

    # Normalizamos únicamente la estructura básica.
    normalized_text = normalize_basic_text(
        text
    )

    # Dividimos la frase en una lista de palabras.
    #
    # Ejemplo:
    #
    #     "que sabes de saray"
    #
    # se convierte en:
    #
    #     ["que", "sabes", "de", "saray"]
    words = normalized_text.split()

    # -------------------------------------------------------------------------
    # CASO 1: "MIS RECUERDOS"
    # -------------------------------------------------------------------------
    #
    # Esta estructura tiene exactamente dos palabras.
    if len(words) == 2:

        # Comprobamos que:
        #
        # - La primera palabra se parezca a "mis".
        # - La segunda se parezca a "recuerdos".
        if (
            words_are_similar(
                words[0],
                "mis",
                cutoff=0.70,
            )
            and
            words_are_similar(
                words[1],
                "recuerdos",
                cutoff=0.72,
            )
        ):

            # Indicamos que la consulta es sobre
            # el usuario activo.
            return {
                "type": "self",
            }

    # -------------------------------------------------------------------------
    # CASO 2:
    #
    # "QUE + SABES/RECUERDAS + DE + PERSONA"
    # -------------------------------------------------------------------------
    #
    # La frase debe tener como mínimo cuatro palabras.
    #
    # Ejemplo:
    #
    #     que sabes de mi
    #
    # También puede tener más si el nombre es compuesto:
    #
    #     que sabes de maria jose
    if len(words) < 4:
        return None

    # La primera palabra debe parecerse a "que".
    if not words_are_similar(
        words[0],
        "que",
        cutoff=0.65,
    ):
        return None

    # La segunda palabra debe parecerse a:
    #
    # - sabes
    # - recuerdas
    if not is_knowledge_verb(
        words[1]
    ):
        return None

    # La tercera palabra debe parecerse a "de".
    if not words_are_similar(
        words[2],
        "de",
        cutoff=0.60,
    ):
        return None

    # -------------------------------------------------------------------------
    # EXTRAER EL PROPIETARIO CONSULTADO
    # -------------------------------------------------------------------------
    #
    # Todo lo que aparece a partir de la cuarta palabra
    # se interpreta como el nombre de la persona.
    #
    # Ejemplo:
    #
    #     ["que", "sabes", "de", "maria", "jose"]
    #
    # owner:
    #
    #     "maria jose"
    owner = " ".join(
        words[3:]
    ).strip()

    # Si no existe nombre, la consulta no es válida.
    if not owner:
        return None

    # -------------------------------------------------------------------------
    # CONSULTA SOBRE EL USUARIO ACTIVO
    # -------------------------------------------------------------------------
    #
    # Si la persona indicada es "mi",
    # la consulta se refiere a quien está usando Atlas.
    if owner in {
        "mi",
        "mí",
    }:

        return {
            "type": "self",
        }

    # -------------------------------------------------------------------------
    # CONSULTA SOBRE OTRA PERSONA
    # -------------------------------------------------------------------------
    return {
        "type": "other",
        "owner": owner,
    }