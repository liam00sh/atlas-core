"""
===============================================================================
Proyecto Atlas
Archivo: utils/text_normalizer.py

Descripción:
    Este módulo normaliza y corrige parcialmente el texto escrito
    por el usuario antes de que Atlas intente interpretarlo.

    Sus responsabilidades principales son:

    - Convertir el texto a minúsculas.
    - Eliminar acentos.
    - Eliminar signos de puntuación.
    - Reducir espacios duplicados.
    - Corregir errores frecuentes definidos manualmente.
    - Reducir letras repetidas accidentalmente.
    - Buscar palabras o frases similares.
    - Ayudar a reconocer comandos escritos con pequeñas erratas.

Ejemplos:

    "QEU SABES DE MÍ"
        -> "que sabes de mi"

    "xorrector"
        -> "corrector"

    "querrrer"
        -> "querer"

    "versoin"
        -> puede resolverse como "version"

Importante:
    Este módulo no comprende el significado completo de una frase.

    Solo realiza normalización y comparación aproximada.
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
# - Reducir espacios duplicados.
# - Reducir letras repetidas.
import re

# unicodedata permite analizar caracteres Unicode.
#
# Se utiliza principalmente para eliminar acentos.
#
# Ejemplo:
#
# "qué" -> "que"
import unicodedata

# get_close_matches busca textos parecidos dentro de una lista.
#
# Se utiliza para corregir palabras o frases con pequeñas erratas.
from difflib import get_close_matches


# =============================================================================
# CORRECCIONES MANUALES
# =============================================================================

# Diccionario de errores conocidos y su forma correcta.
#
# Cada clave representa una forma incorrecta.
# Cada valor representa la corrección.
COMMON_REPLACEMENTS = {

    # Errores habituales al escribir "que".
    "qeu": "que",
    "qe": "que",
    "ue": "que",
    "ke": "que",

    # Errores habituales al escribir "soy".
    "spy": "soy",
    "siy": "soy",

    # Formas frecuentes de órdenes.
    "sbaes": "sabes",
    "sabesr": "sabes",
    "recuerads": "recuerdas",
    "recuardas": "recuerdas",
    "recuerad": "recuerda",
    "recuerdame": "recuerda",

    # -------------------------------------------------------------------------
    # EJEMPLOS DE ERRORES INDICADOS PARA ATLAS
    # -------------------------------------------------------------------------
    "ospital": "hospital",
    "hermita": "ermita",
    "corer": "correr",
    "xorrector": "corrector",
    "correctyor": "corrector",
    "querrrer": "querer",
}


# =============================================================================
# VOCABULARIO COMÚN
# =============================================================================

# Conjunto de palabras que Atlas conoce como correctas.
#
# Se utiliza como base para intentar corregir palabras similares.
#
# Un set es adecuado porque:
#
# - Evita duplicados.
# - Permite búsquedas rápidas.
COMMON_VOCABULARY = {

    "que",
    "sabes",
    "recuerdas",
    "recuerda",
    "de",
    "mi",
    "sobre",
    "soy",
    "usuario",
    "salir",
    "adios",
    "ayuda",
    "hospital",
    "ermita",
    "correr",
    "corrector",
    "querer",
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
        "adiós" -> "adios"
        "Rubén" -> "Ruben"
    """

    # NFD separa las letras de sus marcas de acento.
    #
    # Ejemplo:
    #
    # "é" se transforma en:
    #
    # "e" + marca de acento
    normalized = unicodedata.normalize(
        "NFD",
        text,
    )

    # Reconstruimos el texto ignorando los caracteres
    # cuya categoría Unicode sea "Mn".
    #
    # "Mn" significa:
    #     Marca no espaciada.
    #
    # En este caso, representa los acentos.
    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        ) != "Mn"
    )


def _reduce_repeated_characters(
    word: str,
) -> str:
    """
    Reduce repeticiones excesivas de una misma letra.

    Parámetros:
        word:
            Palabra que se desea corregir.

    Devuelve:
        str:
            Palabra con un máximo de dos caracteres
            consecutivos iguales.

    Ejemplos:
        "querrrrer" -> "querrer"
        "holaaaaa"  -> "holaa"

    Importante:
        No reduce dos letras iguales porque algunas palabras
        correctas pueden contenerlas.

        Ejemplo:
            "correr"
    """

    # Expresión regular:
    #
    # (.)
    #     Captura cualquier carácter.
    #
    # \1{2,}
    #     Busca ese mismo carácter repetido
    #     dos veces más o más.
    #
    # En total detecta tres o más caracteres iguales seguidos.
    #
    # r"\1\1"
    #     Los sustituye por solo dos repeticiones.
    return re.sub(
        r"(.)\1{2,}",
        r"\1\1",
        word,
    )


def _correct_word(
    word: str,
    vocabulary: set[str],
) -> str:
    """
    Intenta corregir una palabra.

    Parámetros:
        word:
            Palabra recibida.

        vocabulary:
            Conjunto de palabras consideradas válidas.

    Devuelve:
        str:
            Palabra corregida o la palabra original normalizada
            si no se encuentra una coincidencia fiable.

    Orden de corrección:

        1. Buscar una sustitución manual exacta.
        2. Reducir letras repetidas.
        3. Volver a buscar una sustitución manual.
        4. Comprobar si ya pertenece al vocabulario.
        5. Buscar una palabra similar.
        6. Mantener la palabra si no hay coincidencia.
    """

    # -------------------------------------------------------------------------
    # 1. SUSTITUCIÓN MANUAL DIRECTA
    # -------------------------------------------------------------------------
    if word in COMMON_REPLACEMENTS:
        return COMMON_REPLACEMENTS[
            word
        ]

    # -------------------------------------------------------------------------
    # 2. REDUCCIÓN DE LETRAS REPETIDAS
    # -------------------------------------------------------------------------
    reduced_word = _reduce_repeated_characters(
        word
    )

    # -------------------------------------------------------------------------
    # 3. SUSTITUCIÓN DESPUÉS DE REDUCIR REPETICIONES
    # -------------------------------------------------------------------------
    if reduced_word in COMMON_REPLACEMENTS:
        return COMMON_REPLACEMENTS[
            reduced_word
        ]

    # -------------------------------------------------------------------------
    # 4. PALABRA YA CONOCIDA
    # -------------------------------------------------------------------------
    if reduced_word in vocabulary:
        return reduced_word

    # -------------------------------------------------------------------------
    # 5. EVITAR CORRECCIONES ARRIESGADAS EN PALABRAS CORTAS
    # -------------------------------------------------------------------------
    #
    # Las palabras cortas tienen muchas coincidencias posibles.
    #
    # Ejemplo:
    #
    # "de", "me", "mi", "si"
    #
    # Corregirlas automáticamente podría producir errores.
    if len(reduced_word) < 4:
        return reduced_word

    # -------------------------------------------------------------------------
    # 6. BÚSQUEDA APROXIMADA
    # -------------------------------------------------------------------------
    #
    # get_close_matches() busca la palabra más parecida
    # dentro del vocabulario.
    #
    # n=1:
    #     Devuelve como máximo una coincidencia.
    #
    # cutoff=0.82:
    #     Exige una similitud mínima del 82 %.
    matches = get_close_matches(
        reduced_word,
        vocabulary,
        n=1,
        cutoff=0.82,
    )

    # Si hay coincidencia, devolvemos la mejor.
    if matches:
        return matches[0]

    # Si no se encuentra una corrección suficientemente fiable,
    # mantenemos la palabra.
    return reduced_word


def normalize_text(
    text: str,
    extra_vocabulary=None,
) -> str:
    """
    Normaliza una frase completa.

    Parámetros:
        text:
            Texto original.

        extra_vocabulary:
            Palabras adicionales que deben considerarse válidas.

            Se utiliza, por ejemplo, para añadir dinámicamente
            nombres de comandos y alias.

    Devuelve:
        str:
            Texto normalizado y parcialmente corregido.

    Ejemplo:
        "QEU SABES DE MÍ?"
            -> "que sabes de mi"
    """

    # -------------------------------------------------------------------------
    # 1. MINÚSCULAS, ESPACIOS Y ACENTOS
    # -------------------------------------------------------------------------
    normalized_text = remove_accents(
        text.lower().strip()
    )

    # -------------------------------------------------------------------------
    # 2. ELIMINAR SIGNOS DE PUNTUACIÓN
    # -------------------------------------------------------------------------
    #
    # [^\w\s]
    #
    # significa:
    #
    # - Todo lo que NO sea una letra, número, guion bajo
    #   o espacio.
    #
    # Cada signo se sustituye por un espacio.
    normalized_text = re.sub(
        r"[^\w\s]",
        " ",
        normalized_text,
    )

    # -------------------------------------------------------------------------
    # 3. REDUCIR ESPACIOS DUPLICADOS
    # -------------------------------------------------------------------------
    #
    # \s+
    #
    # encuentra uno o más espacios consecutivos.
    normalized_text = re.sub(
        r"\s+",
        " ",
        normalized_text,
    ).strip()

    # -------------------------------------------------------------------------
    # 4. CREAR EL VOCABULARIO DE TRABAJO
    # -------------------------------------------------------------------------
    #
    # Creamos una copia para no modificar
    # COMMON_VOCABULARY directamente.
    vocabulary = set(
        COMMON_VOCABULARY
    )

    # Si se ha recibido vocabulario adicional,
    # lo normalizamos y añadimos.
    #
    # Ejemplo:
    #
    # COMMANDS.keys()
    if extra_vocabulary:

        vocabulary.update(
            remove_accents(
                str(item).lower()
            )
            for item in extra_vocabulary
        )

    # -------------------------------------------------------------------------
    # 5. CORREGIR CADA PALABRA
    # -------------------------------------------------------------------------
    #
    # split() separa el texto por espacios.
    #
    # La comprensión de listas procesa cada palabra
    # mediante _correct_word().
    corrected_words = [
        _correct_word(
            word,
            vocabulary,
        )
        for word in normalized_text.split()
    ]

    # -------------------------------------------------------------------------
    # 6. RECONSTRUIR LA FRASE
    # -------------------------------------------------------------------------
    #
    # " ".join(...) une las palabras utilizando
    # un espacio entre ellas.
    return " ".join(
        corrected_words
    )


def find_closest_phrase(
    text: str,
    candidates,
    cutoff: float = 0.84,
) -> str | None:
    """
    Busca la frase candidata más parecida al texto recibido.

    Parámetros:
        text:
            Frase escrita por el usuario.

        candidates:
            Colección de frases válidas.

        cutoff:
            Similitud mínima aceptada.

            Por defecto:
                0.84, equivalente aproximadamente al 84 %.

    Devuelve:
        str:
            Frase candidata encontrada.

        None:
            Ninguna frase es suficientemente parecida.

    Ejemplo:
        Texto:
            "versoin"

        Candidatos:
            ["version", "fecha", "ayuda"]

        Resultado:
            "version"
    """

    # Normalizamos todas las frases candidatas.
    normalized_candidates = [
        normalize_text(candidate)
        for candidate in candidates
    ]

    # Normalizamos el texto recibido usando también
    # las candidatas como vocabulario adicional.
    normalized_text = normalize_text(
        text,
        normalized_candidates,
    )

    # Si existe una coincidencia exacta después
    # de normalizar, la devolvemos directamente.
    if normalized_text in normalized_candidates:
        return normalized_text

    # Buscamos la frase más parecida.
    matches = get_close_matches(
        normalized_text,
        normalized_candidates,
        n=1,
        cutoff=cutoff,
    )

    # Si no existe ninguna coincidencia válida,
    # devolvemos None.
    if not matches:
        return None

    # Devolvemos la mejor coincidencia.
    return matches[0]