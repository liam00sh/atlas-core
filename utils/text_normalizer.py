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

    Las correcciones se aplican palabra por palabra.

    Esto evita reemplazos incorrectos dentro de palabras válidas.

    Ejemplo:

        "recuerdos"

    debe mantenerse como:

        "recuerdos"

    y no convertirse erróneamente en:

        "recuerdas"

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
# Cada clave representa una palabra incorrecta completa.
# Cada valor representa su corrección.
#
# Estas sustituciones nunca deben aplicarse mediante replace()
# sobre una frase completa, porque eso podría modificar fragmentos
# contenidos dentro de palabras válidas.
COMMON_REPLACEMENTS = {

    # -------------------------------------------------------------------------
    # ERRORES HABITUALES AL ESCRIBIR "QUE"
    # -------------------------------------------------------------------------

    "qeu": "que",
    "qe": "que",
    "ue": "que",
    "ke": "que",

    # -------------------------------------------------------------------------
    # ERRORES HABITUALES AL ESCRIBIR "SOY"
    # -------------------------------------------------------------------------

    "spy": "soy",
    "siy": "soy",

    # -------------------------------------------------------------------------
    # FORMAS FRECUENTES DE ÓRDENES
    # -------------------------------------------------------------------------

    "sbaes": "sabes",
    "sabesr": "sabes",

    "recuerads": "recuerdas",
    "recuardas": "recuerdas",
    "recuerad": "recuerda",
    "recuerdame": "recuerda",

    "contecto": "contexto",

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
# Es importante incluir tanto verbos como sustantivos relacionados.
#
# Por ejemplo:
#
# - recuerda
# - recuerdas
# - recuerdo
# - recuerdos
#
# De lo contrario, la búsqueda aproximada podría transformar
# incorrectamente "recuerdos" en "recuerdas".
COMMON_VOCABULARY = {

    # -------------------------------------------------------------------------
    # PALABRAS GENERALES
    # -------------------------------------------------------------------------

    "a",
    "al",
    "algo",
    "como",
    "con",
    "cual",
    "cuando",
    "cuanta",
    "cuantas",
    "cuanto",
    "cuantos",
    "de",
    "del",
    "dime",
    "donde",
    "el",
    "en",
    "es",
    "esta",
    "estado",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "para",
    "por",
    "que",
    "quien",
    "se",
    "sobre",
    "soy",
    "su",
    "sus",
    "te",
    "tengo",
    "tiene",
    "tu",
    "un",
    "una",
    "usuario",
    "y",
    "yo",

    # -------------------------------------------------------------------------
    # MEMORIA Y CONTEXTO
    # -------------------------------------------------------------------------

    "memoria",
    "memorias",
    "recuerda",
    "recuerdas",
    "recuerdo",
    "recuerdos",
    "recordar",
    "contexto",
    "conversacion",

    # -------------------------------------------------------------------------
    # COMANDOS Y ACCIONES
    # -------------------------------------------------------------------------

    "adios",
    "ayuda",
    "cancelar",
    "confirmar",
    "salir",
    "sabes",

    # -------------------------------------------------------------------------
    # SISTEMA Y HERRAMIENTAS
    # -------------------------------------------------------------------------

    "bateria",
    "cpu",
    "disco",
    "gpu",
    "hora",
    "informacion",
    "internet",
    "memoria",
    "ordenador",
    "python",
    "ram",
    "red",
    "sistema",
    "version",

    # -------------------------------------------------------------------------
    # VOCABULARIO DE EJEMPLO
    # -------------------------------------------------------------------------

    "hospital",
    "ermita",
    "correr",
    "corrector",
    "querer",
}


# =============================================================================
# ELIMINACIÓN DE ACENTOS
# =============================================================================

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
    #
    #     Marca no espaciada.
    #
    # En este caso representa los acentos.
    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        ) != "Mn"
    )


# =============================================================================
# REDUCCIÓN DE CARACTERES REPETIDOS
# =============================================================================

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
    #     Los sustituye por dos repeticiones.
    return re.sub(
        r"(.)\1{2,}",
        r"\1\1",
        word,
    )


# =============================================================================
# PREPARACIÓN DEL VOCABULARIO ADICIONAL
# =============================================================================

def _extract_extra_vocabulary_words(
    extra_vocabulary,
) -> set[str]:
    """
    Convierte un vocabulario adicional en palabras normalizadas.

    Parámetros:
        extra_vocabulary:
            Colección de comandos, alias, palabras o frases.

    Devuelve:
        set[str]:
            Palabras individuales normalizadas.

    Ejemplo:
        Entrada:

            [
                "cambiar usuario",
                "estado",
            ]

        Salida:

            {
                "cambiar",
                "usuario",
                "estado",
            }

    Esto evita guardar una frase completa como un único elemento
    cuando posteriormente la corrección se realiza palabra por palabra.
    """

    vocabulary_words = set()

    if not extra_vocabulary:
        return vocabulary_words

    for item in extra_vocabulary:

        normalized_item = remove_accents(
            str(item).lower().strip()
        )

        normalized_item = re.sub(
            r"[^\w\s]",
            " ",
            normalized_item,
        )

        normalized_item = re.sub(
            r"\s+",
            " ",
            normalized_item,
        ).strip()

        if not normalized_item:
            continue

        vocabulary_words.update(
            normalized_item.split()
        )

    return vocabulary_words


# =============================================================================
# CORRECCIÓN DE PALABRAS
# =============================================================================

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
        5. Mantener números sin cambios.
        6. Evitar correcciones arriesgadas en palabras cortas.
        7. Buscar una palabra similar.
        8. Mantener la palabra si no hay coincidencia.
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
    # 5. NÚMEROS
    # -------------------------------------------------------------------------

    # No intentamos corregir números ni cadenas
    # formadas exclusivamente por dígitos.
    if reduced_word.isdigit():

        return reduced_word

    # -------------------------------------------------------------------------
    # 6. EVITAR CORRECCIONES ARRIESGADAS EN PALABRAS CORTAS
    # -------------------------------------------------------------------------

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
    # 7. BÚSQUEDA APROXIMADA
    # -------------------------------------------------------------------------

    # Usamos un umbral algo más estricto para palabras largas.
    #
    # Esto reduce correcciones incorrectas entre palabras legítimas
    # que se parecen entre sí, como:
    #
    # recuerdos
    # recuerdas
    cutoff = (
        0.88
        if len(reduced_word) >= 7
        else 0.84
    )

    matches = get_close_matches(
        reduced_word,
        vocabulary,
        n=1,
        cutoff=cutoff,
    )

    if matches:

        return matches[0]

    # -------------------------------------------------------------------------
    # 8. PALABRA SIN CORRECCIÓN FIABLE
    # -------------------------------------------------------------------------

    return reduced_word


# =============================================================================
# NORMALIZACIÓN DE FRASES
# =============================================================================

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
            Palabras o frases adicionales que deben considerarse válidas.

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
    # 1. VALIDACIÓN BÁSICA
    # -------------------------------------------------------------------------

    if not isinstance(
        text,
        str,
    ):

        text = str(
            text
        )

    # -------------------------------------------------------------------------
    # 2. MINÚSCULAS, ESPACIOS Y ACENTOS
    # -------------------------------------------------------------------------

    normalized_text = remove_accents(
        text.lower().strip()
    )

    # -------------------------------------------------------------------------
    # 3. ELIMINAR SIGNOS DE PUNTUACIÓN
    # -------------------------------------------------------------------------

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
    # 4. REDUCIR ESPACIOS DUPLICADOS
    # -------------------------------------------------------------------------

    normalized_text = re.sub(
        r"\s+",
        " ",
        normalized_text,
    ).strip()

    if not normalized_text:

        return ""

    # -------------------------------------------------------------------------
    # 5. CREAR EL VOCABULARIO DE TRABAJO
    # -------------------------------------------------------------------------

    # Creamos una copia para no modificar
    # COMMON_VOCABULARY directamente.
    vocabulary = set(
        COMMON_VOCABULARY
    )

    # Añadimos las palabras de las correcciones manuales.
    #
    # De este modo tanto las formas erróneas como sus resultados
    # forman parte del contexto conocido del normalizador.
    vocabulary.update(
        COMMON_REPLACEMENTS.values()
    )

    # Añadimos palabras procedentes de comandos,
    # alias u otros elementos dinámicos.
    vocabulary.update(
        _extract_extra_vocabulary_words(
            extra_vocabulary
        )
    )

    # -------------------------------------------------------------------------
    # 6. CORREGIR CADA PALABRA
    # -------------------------------------------------------------------------

    corrected_words = [

        _correct_word(
            word,
            vocabulary,
        )

        for word in normalized_text.split()

    ]

    # -------------------------------------------------------------------------
    # 7. RECONSTRUIR LA FRASE
    # -------------------------------------------------------------------------

    return " ".join(
        corrected_words
    )


# =============================================================================
# COMPARACIÓN DE FRASES
# =============================================================================

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
            [
                "version",
                "fecha",
                "ayuda",
            ]

        Resultado:
            "version"
    """

    # Convertimos primero la colección para poder recorrerla
    # más de una vez aunque se trate de un generador.
    candidate_list = [

        str(candidate)

        for candidate in candidates

    ]

    if not candidate_list:

        return None

    # Normalizamos todas las frases candidatas.
    normalized_candidates = [

        normalize_text(
            candidate
        )

        for candidate in candidate_list

    ]

    # Eliminamos posibles cadenas vacías.
    normalized_candidates = [

        candidate

        for candidate in normalized_candidates

        if candidate

    ]

    if not normalized_candidates:

        return None

    # Normalizamos el texto recibido usando también
    # las candidatas como vocabulario adicional.
    normalized_text = normalize_text(
        text,
        normalized_candidates,
    )

    if not normalized_text:

        return None

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

    if not matches:

        return None

    return matches[0]