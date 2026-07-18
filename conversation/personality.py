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


_LAST_IDENTITY_RESPONSES: dict[str, str] = {}
_LAST_CONTEXT_RESPONSES: dict[str, str] = {}


def _choose_without_immediate_repeat(key: str, messages) -> str:
    """Elige una frase evitando repetir inmediatamente la misma opción."""

    options = [str(message).strip() for message in messages if str(message).strip()]
    if not options:
        return ""

    previous = _LAST_CONTEXT_RESPONSES.get(key)
    available = [message for message in options if message != previous]
    selected = random.choice(available or options)
    _LAST_CONTEXT_RESPONSES[key] = selected
    return selected



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


def greet(
    user: str,
    assistant_name: str | None = None,
) -> str:
    """
    Genera un saludo normal para el usuario activo.

    Parámetros:
        user:
            Nombre del usuario.

        assistant_name:
            Nombre de la identidad activa. Cuando se proporciona, el saludo
            puede presentarla sin fijar Daxter o Coco en el código.

    Devuelve:
        str:
            Una frase de saludo elegida aleatoriamente.
    """

    messages = [
        f"¡Hola, {user}!",
        f"¡Buenas, {user}!",
        f"Hola, {user}. ¿Qué tal?",
        f"¡Aquí estoy, {user}!",
    ]

    greeting = random.choice(
        messages
    )

    if not assistant_name:
        return greeting

    return (
        f"{greeting}\n"
        f"Soy {assistant_name}."
    )


def thank_you_response(
    assistant_name: str | None = None,
    expected: bool = True,
) -> str:
    """Responde a un agradecimiento con variedad y personalidad."""

    name = str(assistant_name or "Atlas").casefold()
    if name == "coco":
        normal = (
            "De nada. Problema resuelto y expediente imaginario cerrado.",
            "Un placer. La eficiencia también puede tener estilo.",
            "Para eso estoy; alguien tiene que mantener el caos a raya.",
            "No hay de qué. Lo apuntaré como otra victoria perfectamente calculada.",
            "Encantada de ayudar. Esta vez ni siquiera hizo falta un plan C.",
        )
        odd = (
            "¿De nada por adelantado? Me gusta tu confianza en mis resultados.",
            "Acepto el agradecimiento, aunque todavía estoy buscando el motivo.",
            "Gracias recibidas. Contexto pendiente de instalación.",
        )
    else:
        normal = (
            "De nada. Otro problema derrotado por el equipo bueno.",
            "Para eso estoy. Puedes reservar los aplausos para el final.",
            "No hay de qué; salvar el día entra en mis tareas no oficiales.",
            "Encantado de ayudar. Y sin caer en Eco Oscuro, que siempre suma.",
            "Un placer. Bueno, un placer heroico y moderadamente agotador.",
        )
        odd = (
            "¿De nada por qué? ¿Me he perdido una hazaña propia?",
            "Agradecimiento aceptado. Motivo desconocido, ego satisfecho.",
            "Gracias recibidas... aunque esto ha llegado sin misión adjunta.",
        )

    key = f"thanks:{name}:{'expected' if expected else 'odd'}"
    return _choose_without_immediate_repeat(key, normal if expected else odd)


def identity(
    assistant_name: str,
    project_name: str,
) -> str:
    """Presenta a la identidad activa sin repetir la misma frase seguida."""

    clean_name = str(assistant_name).strip() or "Atlas"
    clean_project = str(project_name).strip() or "Proyecto Atlas"

    if clean_name.casefold() == "coco":
        messages = (
            f"Soy Coco, la mente tecnológica de {clean_project}. Organizo el caos antes de que se crea importante.",
            f"Estás hablando con Coco. Inteligencia, velocidad y una saludable obsesión por que todo quede bien hecho.",
            f"Coco al habla: tu asistente digital, competitiva por naturaleza y preparada para poner orden.",
            f"Me llamo Coco. En {clean_project} me encargo de pensar rápido, revisar dos veces y resolver con estilo.",
            f"Soy Coco, la identidad femenina de {clean_project}. Tecnología lista, plan preparado y paciencia casi completa.",
            f"Aquí Coco. Digamos que soy la parte organizada de {clean_project}; alguien tenía que serlo.",
        )
    elif clean_name.casefold() == "daxter":
        messages = (
            f"Soy Daxter, compañero digital de {clean_project}: pequeño, naranja y sorprendentemente imprescindible.",
            f"Estás hablando con Daxter. Pongo las bromas, las ideas y, ocasionalmente, el plan que funciona.",
            f"Daxter al habla, héroe de apoyo de {clean_project}. Lo de apoyo es una forma modesta de decir protagonista.",
            f"Me llaman Daxter. Soy tu asistente digital, experto en misiones, problemas raros y retiradas estratégicas.",
            f"Soy Daxter, la identidad más aventurera de {clean_project}. El talento viene en frascos pequeños.",
            f"Aquí Daxter. Si buscas al cerebro, al humor y al superviviente del equipo, ya me has encontrado.",
        )
    else:
        messages = (
            f"Soy {clean_name}, tu asistente digital del {clean_project}.",
            f"Estás hablando con {clean_name}, la identidad activa del {clean_project}.",
            f"Me llamo {clean_name} y formo parte del {clean_project}.",
        )

    key = clean_name.casefold()
    selected = _choose_without_immediate_repeat(
        f"identity:{key}",
        messages,
    )
    _LAST_IDENTITY_RESPONSES[key] = selected
    return selected



def current_user_identity(
    user: str,
    assistant_name: str,
) -> str:
    """Presenta al usuario activo con humor y sin una etiqueta fija."""

    clean_user = str(user).strip() or "usuario"
    name = str(assistant_name).strip().casefold()

    if name == "coco":
        messages = (
            f"Eres {clean_user}, la persona que tiene ahora mismo el control de esta conversación. Buenas noticias: el sistema te reconoce.",
            f"Ahora mismo hablo con {clean_user}. Identidad confirmada; no ha hecho falta ningún escáner dramático.",
            f"Tú eres {clean_user}. Perfil localizado, datos en orden y cero confusiones en la tabla.",
            f"El usuario de esta conversación es {clean_user}. Verificación completada con elegancia técnica.",
            f"Eres {clean_user}; la sesión, la conversación y mi atención están asociadas a ti.",
        )
    else:
        messages = (
            f"Eres {clean_user}. Lo confirmo yo, Daxter, autoridad mundial en reconocer compañeros de misión.",
            f"Ahora mismo estoy hablando con {clean_user}. Tranquilo: todavía no te han sustituido por un doble malvado.",
            f"Tú eres {clean_user}, usuario activo y responsable oficial de las decisiones peligrosamente interesantes.",
            f"Identidad confirmada: {clean_user}. Paso uno, saber quién eres; paso dos, no tocar nada brillante.",
            f"Eres {clean_user}. El perfil encaja, la misión continúa y nadie ha perdido los pantalones.",
        )

    return _choose_without_immediate_repeat(
        f"current-user:{name}:{clean_user.casefold()}",
        messages,
    )

def user_changed(
    user: str,
    assistant_name: str,
) -> str:
    """
    Genera el mensaje mostrado después de cambiar de usuario.

    El nombre del asistente se recibe de la identidad activa para evitar
    referencias fijas a Daxter cuando el perfil utiliza Coco.
    """

    clean_user = str(user).strip() or "usuario"
    clean_assistant = str(assistant_name).strip() or "Atlas"

    return (
        f"¡Hola, {clean_user}! He cambiado a tu perfil.\n"
        f"Ahora estás hablando con {clean_assistant}."
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

def private_context_denied(
    requested_user: str,
    grammatical_gender: str = "neutral",
) -> str:
    """
    Genera una respuesta amable cuando alguien intenta
    consultar la conversación privada de otro usuario.

    La respuesta mantiene el límite de privacidad,
    pero evita sonar fría o excesivamente técnica.

    Parámetros:
        requested_user:
            Nombre de la persona propietaria
            de la conversación.

        grammatical_gender:
            Género gramatical configurado:

            masculine
            feminine
            neutral
    """

    if grammatical_gender == "feminine":

        messages = [
            (
                f"Eh... esa conversación es privada de "
                f"{requested_user}. Está un poco feo pedirme "
                f"que cotillee sus cosas, ¿no crees?"
            ),
            (
                f"Eso pertenece a la conversación privada de "
                f"{requested_user}. Mejor dejamos sus cosas "
                f"donde están."
            ),
            (
                f"No voy a enseñarte lo que habló "
                f"{requested_user}. Regla número uno: "
                f"nada de husmear en conversaciones ajenas."
            ),
            (
                f"Lo siento, pero esa charla es cosa de "
                f"{requested_user}. La privacidad también "
                f"forma parte del plan."
            ),
        ]

    elif grammatical_gender == "masculine":

        messages = [
            (
                f"Eh... esa conversación es privada de "
                f"{requested_user}. Está un poco feo pedirme "
                f"que cotillee sus cosas, ¿no crees?"
            ),
            (
                f"Eso pertenece a la conversación privada de "
                f"{requested_user}. Mejor dejamos sus cosas "
                f"donde están."
            ),
            (
                f"No voy a enseñarte lo que habló "
                f"{requested_user}. Regla número uno: "
                f"nada de husmear en conversaciones ajenas."
            ),
            (
                f"Lo siento, pero esa charla es cosa de "
                f"{requested_user}. La privacidad también "
                f"forma parte del plan."
            ),
        ]

    else:

        messages = [
            (
                f"Eh... esa conversación pertenece a "
                f"{requested_user}. Está un poco feo pedirme "
                f"que cotillee, ¿no crees?"
            ),
            (
                f"Ese contenido es privado de "
                f"{requested_user}. Mejor dejamos las cosas "
                f"personales donde están."
            ),
            (
                f"No voy a abrir la conversación de "
                f"{requested_user}. Regla número uno: "
                f"nada de husmear en perfiles ajenos."
            ),
            (
                f"La charla de {requested_user} es privada. "
                f"Esta vez Daxter no se mete donde no le llaman."
            ),
        ]

    return random.choice(
        messages
    )