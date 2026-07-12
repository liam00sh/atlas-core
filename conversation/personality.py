"""
===============================================================================
Proyecto Atlas
Archivo: conversation/personality.py

Descripción:
    Este módulo centraliza la personalidad verbal de Daxter.

    Su responsabilidad es generar frases para distintos contextos:

    - Saludo inicial.
    - Saludos normales.
    - Agradecimientos.
    - Presentación del asistente.
    - Cambio de usuario.
    - Regreso al usuario principal.
    - Despedida final.
    - Entradas no entendidas.
    - Confirmación de recuerdos guardados.

    Las frases pueden proceder de dos fuentes:

    1. ORIGINAL_PHRASES
        Frases originales creadas específicamente para Atlas.

    2. GAME_REFERENCES
        Referencias inspiradas o extraídas de los juegos de Daxter.

    La función choose_phrase() decide qué fuente utilizar.

Importante:
    Este archivo no detecta intenciones ni ejecuta acciones.

    Únicamente devuelve textos que otros módulos muestran al usuario.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# El módulo random permite elegir una opción aleatoria
# dentro de una lista de frases.
import random


# Diccionario con referencias procedentes de los videojuegos.
#
# Ejemplo:
#
# GAME_REFERENCES = {
#     "startup": [
#         "¡A darle caña!",
#         ...
#     ],
#     "farewell": [
#         ...
#     ],
# }
from conversation.game_references import GAME_REFERENCES

# Diccionario con frases originales creadas para Atlas.
#
# Ejemplo:
#
# ORIGINAL_PHRASES = {
#     "startup": [
#         "Daxter en marcha.",
#         ...
#     ],
#     "memory_saved": [
#         ...
#     ],
# }
from conversation.original_phrases import ORIGINAL_PHRASES


def choose_phrase(
    category: str,
    game_reference_probability: float = 1.0,
) -> str:
    """
    Elige una frase asociada a una categoría.

    Parámetros:
        category:
            Categoría de frase solicitada.

            Ejemplos:
                "startup"
                "farewell"
                "memory_saved"
                "not_understood"

        game_reference_probability:
            Probabilidad de elegir una referencia del videojuego.

            Valores posibles:

                0.0
                    Nunca utiliza referencias del juego.

                0.05
                    Aproximadamente un 5 % de las veces.

                0.50
                    Aproximadamente la mitad de las veces.

                1.0
                    Siempre utiliza una referencia del juego,
                    siempre que exista alguna en esa categoría.

    Devuelve:
        str:
            Una frase seleccionada.

            Si no encuentra ninguna frase, devuelve una cadena vacía:
                ""
    """

    # Obtenemos las frases originales de la categoría solicitada.
    #
    # get(category, []) significa:
    #
    # - Si existe la categoría, devuelve su lista.
    # - Si no existe, devuelve una lista vacía.
    original_options = ORIGINAL_PHRASES.get(
        category,
        [],
    )

    # Obtenemos las referencias del juego
    # pertenecientes a esa misma categoría.
    game_options = GAME_REFERENCES.get(
        category,
        [],
    )

    # Decidimos si debe utilizarse una referencia del juego.
    #
    # bool(game_options)
    #     Comprueba que exista al menos una referencia.
    #
    # random.random()
    #     Genera un número decimal aleatorio entre 0.0 y 1.0.
    #
    # Ejemplo con probabilidad 0.05:
    #
    #     0.03 < 0.05  -> True
    #     0.70 < 0.05  -> False
    use_game_reference = (
        bool(game_options)
        and random.random() < game_reference_probability
    )

    # Si se ha decidido usar una referencia,
    # seleccionamos una de forma aleatoria.
    if use_game_reference:
        return random.choice(
            game_options
        )

    # Si no se utiliza una referencia del juego,
    # intentamos devolver una frase original.
    if original_options:
        return random.choice(
            original_options
        )

    # Si no había frases originales, pero sí referencias,
    # utilizamos una referencia como alternativa.
    if game_options:
        return random.choice(
            game_options
        )

    # Si no hay frases en ninguna fuente,
    # devolvemos una cadena vacía.
    return ""


def initial_welcome(
    user: str,
    assistant_name: str,
) -> str:
    """
    Genera el saludo inicial mostrado al arrancar Atlas.

    Parámetros:
        user:
            Nombre del usuario activo.

        assistant_name:
            Nombre del asistente.

    Devuelve:
        str:
            Saludo inicial completo.
    """

    # Seleccionamos una frase de la categoría "startup".
    phrase = choose_phrase(
        "startup"
    )

    # Construimos el mensaje completo.
    #
    # \n representa un salto de línea.
    #
    # \n\n deja una línea vacía entre frases.
    return (
        f"Hola {user}.\n\n"
        f"Soy {assistant_name}.\n\n"
        f"{phrase}\n\n"
        "¿Qué hacemos hoy?"
    )


def greet(user: str) -> str:
    """
    Genera un saludo normal para el usuario activo.

    Parámetros:
        user:
            Nombre del usuario.

    Devuelve:
        str:
            Una frase de saludo elegida aleatoriamente.
    """

    # Lista de posibles saludos.
    messages = [
        f"¡Hola, {user}!",
        f"¡Buenas, {user}!",
        f"Hola, {user}. ¿Qué tal?",
        f"¡Aquí estoy, {user}!",
    ]

    # Elegimos uno de los mensajes al azar.
    return random.choice(
        messages
    )


def thank_you_response() -> str:
    """
    Genera una respuesta cuando el usuario da las gracias.

    No recibe parámetros.

    Devuelve:
        str:
            Una respuesta de agradecimiento.
    """

    messages = [
        "De nada.",
        "Para eso estoy.",
        "Encantado de ayudar.",
        "No hay de qué.",
        "Siempre que lo necesites.",
    ]

    return random.choice(
        messages
    )


def identity(
    assistant_name: str,
    project_name: str,
) -> str:
    """
    Explica quién es Daxter.

    Parámetros:
        assistant_name:
            Nombre del asistente.

        project_name:
            Nombre del proyecto.

    Devuelve:
        str:
            Presentación breve del asistente.
    """

    return (
        f"Soy {assistant_name}, "
        f"el compañero digital del {project_name}.\n\n"
        "Todavía estoy aprendiendo, "
        "pero cada día tengo alguna función nueva."
    )


def user_changed(user: str) -> str:
    """
    Genera el mensaje mostrado al cambiar de usuario.

    Parámetros:
        user:
            Nombre del nuevo usuario activo.

    Devuelve:
        str:
            Mensaje de bienvenida personalizado.
    """

    # Obtenemos las frases originales de bienvenida
    # para usuarios temporales.
    messages = ORIGINAL_PHRASES.get(
        "guest_welcome",
        [],
    )

    # Si existen frases configuradas,
    # elegimos una aleatoriamente.
    if messages:

        # Algunas frases contienen el marcador:
        #
        #     {user}
        #
        # format() lo sustituye por el nombre real.
        return random.choice(
            messages
        ).format(
            user=user
        )

    # Respuesta alternativa si la categoría
    # guest_welcome no existe o está vacía.
    return (
        f"¡Hola, {user}!\n\n"
        "He cambiado a tu perfil.\n\n"
        "¿Qué hacemos hoy?"
    )


def returned_to_main(
    previous_user: str,
    main_user: str,
) -> str:
    """
    Genera el mensaje de despedida de un usuario temporal
    y el regreso al usuario principal.

    Parámetros:
        previous_user:
            Usuario temporal que abandona la sesión.

        main_user:
            Usuario principal al que vuelve Atlas.

    Devuelve:
        str:
            Mensaje completo de transición.
    """

    # Buscamos frases configuradas para el regreso a Liam.
    messages = ORIGINAL_PHRASES.get(
        "return_to_liam",
        [],
    )

    # Si existen frases, utilizamos una de ellas.
    if messages:

        return (
            f"Adiós, {previous_user}.\n\n"
            + random.choice(
                messages
            ).format(
                main_user=main_user
            )
            + "\n\n¿Qué hacemos ahora?"
        )

    # Mensaje alternativo si no hay frases configuradas.
    return (
        f"Adiós, {previous_user}.\n\n"
        f"Vuelvo con {main_user}, "
        "que es mi usuario principal.\n\n"
        f"Hola de nuevo, {main_user}.\n\n"
        "¿Qué hacemos ahora?"
    )


def final_goodbye(user: str) -> str:
    """
    Genera la despedida definitiva al cerrar Atlas.

    Parámetros:
        user:
            Usuario que está cerrando el asistente.

    Devuelve:
        str:
            Mensaje final de despedida.
    """

    # Seleccionamos una frase de despedida.
    phrase = choose_phrase(
        "farewell"
    )

    return (
        f"Adiós, {user}.\n\n"
        f"{phrase}\n\n"
        "Hasta pronto."
    )


def not_understood() -> str:
    """
    Genera una respuesta cuando Daxter no comprende la entrada.

    No recibe parámetros.

    Devuelve:
        str:
            Mensaje de entrada no entendida.
    """

    # Pedimos una frase de la categoría "not_understood".
    phrase = choose_phrase(
        "not_understood"
    )

    # Si existe una frase válida, la devolvemos.
    if phrase:
        return phrase

    # Respuesta segura si no existe esa categoría
    # en ninguno de los diccionarios.
    return "No te he entendido."


def memory_saved() -> str:
    """
    Genera una respuesta cuando se guarda un recuerdo.

    No recibe parámetros.

    Devuelve:
        str:
            Mensaje de confirmación de memoria.
    """

    # Seleccionamos una frase de la categoría "memory_saved".
    phrase = choose_phrase(
        "memory_saved"
    )

    if phrase:
        return phrase

    # Respuesta alternativa si no hay frases configuradas.
    return "Entendido. Lo recordaré."