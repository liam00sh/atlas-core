"""
===============================================================================
Proyecto Atlas
Archivo: conversation/intent.py

Descripción:
    Este módulo detecta intenciones conversacionales sencillas que no
    necesitan todavía una inteligencia artificial.

    Actualmente reconoce:

    - Presentaciones y cambios de usuario.
    - Saludos.
    - Agradecimientos.
    - Preguntas sobre la identidad activa del asistente.

    La memoria y los comandos no se gestionan en este archivo.

    La memoria se procesa desde:

        core/atlas.py

    Los comandos se procesan desde:

        console/command_manager.py

Flujo:

    Texto del usuario
          │
          ▼
    normalize_text()
          │
          ▼
    detect()
          │
          ├── Cambio de usuario
          ├── Saludo
          ├── Agradecimiento
          ├── Identidad
          └── None si no reconoce la intención

Importante:
    Esta es una capa de conversación basada en reglas.

    Todavía no comprende realmente el lenguaje natural como lo hará
    posteriormente el modelo de inteligencia artificial local.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES DEL SISTEMA DE PERSONALIDAD
# =============================================================================

# Genera un saludo adaptado al usuario activo.
#
# Ejemplo:
#
#     ¡Hola, Liam!
from conversation.personality import greet

# Genera la respuesta cuando se pregunta por la identidad activa.
from conversation.personality import identity

# Genera una respuesta cuando el usuario da las gracias.
from conversation.personality import thank_you_response

# Genera el mensaje mostrado después de cambiar de usuario.
from conversation.personality import user_changed


# =============================================================================
# CONTEXTO COMPARTIDO
# =============================================================================

# Permite acceder a la instancia principal de Atlas.
#
# Ejemplos:
#
#     context.atlas.get_user()
#     context.atlas.change_user("Saray")
from core import context


# =============================================================================
# NORMALIZACIÓN DE TEXTO
# =============================================================================

# Corrige y normaliza la entrada antes de compararla.
#
# Entre otras cosas:
#
# - Convierte mayúsculas en minúsculas.
# - Elimina acentos.
# - Elimina signos de puntuación.
# - Corrige determinadas erratas.
# - Reduce espacios duplicados.
from utils.text_normalizer import normalize_text


def _change_to_declared_user(user: str) -> str:
    """
    Cambia de usuario solo cuando el nombre representa a una persona.

    Los animales registrados nunca pueden convertirse en usuarios ni en
    interlocutores, aunque el usuario escriba expresiones como «soy Funcio».
    """

    clean_user = str(user).strip().title()

    if not clean_user:
        return "No he entendido el nombre del usuario."

    atlas = context.atlas
    people_manager = getattr(atlas, "people_manager", None)

    if people_manager is not None:
        animal = people_manager.find_animal_by_name(clean_user)

        if animal is not None:
            return (
                f"{animal.name} es un animal registrado y no puede "
                "iniciar sesión ni hablar con Atlas."
            )

        person = people_manager.find_person_by_name(clean_user)

        if person is not None and person.user_profile:
            clean_user = person.user_profile

    atlas.change_user(clean_user)

    return user_changed(
        clean_user,
        atlas.get_name(),
    )


def detect(text: str) -> str | None:
    """
    Detecta una intención conversacional sencilla.

    Parámetros:
        text:
            Texto original escrito por el usuario.

    Devuelve:
        str:
            Una respuesta cuando se reconoce una intención.

        None:
            Cuando este módulo no sabe interpretar el texto.

    El valor None indica a Atlas que debe probar otra capa
    de procesamiento o mostrar un mensaje de entrada desconocida.
    """

    # Normalizamos el texto para facilitar las comparaciones.
    #
    # Ejemplos:
    #
    #     "HOLA"           -> "hola"
    #     "Quién eres"     -> "quien eres"
    #     "Hola, soy Saray" -> "hola soy saray"
    text = normalize_text(text)

    # -------------------------------------------------------------------------
    # CAMBIO DE USUARIO: "soy Saray"
    # -------------------------------------------------------------------------

    # startswith() comprueba si el texto comienza por una expresión.
    #
    # Ejemplo:
    #
    #     "soy saray".startswith("soy ")
    #
    # devuelve True.
    if text.startswith("soy "):

        # Eliminamos los primeros cuatro caracteres:
        #
        # "soy "
        #
        # y conservamos el nombre.
        #
        # Ejemplo:
        #
        #     "soy saray"
        #          ↓
        #     "saray"
        #
        # title() coloca la primera letra en mayúscula:
        #
        #     "saray" -> "Saray"
        user = text[4:].strip().title()

        # Esta comprobación protege ante una presentación
        # sin ningún nombre válido.
        if not user:

            return (
                "No he entendido el nombre del usuario."
            )

        return _change_to_declared_user(user)

    # -------------------------------------------------------------------------
    # CAMBIO DE USUARIO: "me llamo Saray"
    # -------------------------------------------------------------------------

    if text.startswith("me llamo "):

        # "me llamo " ocupa nueve caracteres.
        user = text[9:].strip().title()

        if not user:

            return (
                "No he entendido el nombre del usuario."
            )

        return _change_to_declared_user(user)

    # -------------------------------------------------------------------------
    # CAMBIO DE USUARIO: "hola, soy Saray"
    # -------------------------------------------------------------------------
    #
    # normalize_text() elimina la coma, por lo que la expresión queda:
    #
    #     "hola soy saray"
    #
    # Por eso comprobamos "hola soy " y no "hola, soy ".
    if text.startswith("hola soy "):

        # "hola soy " ocupa nueve caracteres.
        user = text[9:].strip().title()

        if not user:

            return (
                "No he entendido el nombre del usuario."
            )

        return _change_to_declared_user(user)

    # -------------------------------------------------------------------------
    # SALUDOS
    # -------------------------------------------------------------------------

    # Un conjunto permite comprobar rápidamente si el texto
    # coincide con alguna expresión conocida.
    #
    # Como normalize_text() elimina los acentos, no es necesario
    # repetir aquí "días" y "dias".
    if text in {
        "hola",
        "buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
    }:

        # Obtenemos el usuario activo y generamos
        # un saludo personalizado.
        return greet(
            user=context.atlas.get_user(),
            assistant_name=(
                context.atlas.get_name()
            ),
        )

    # -------------------------------------------------------------------------
    # AGRADECIMIENTOS
    # -------------------------------------------------------------------------

    if text in {
        "gracias",
        "muchas gracias",
        "te lo agradezco",
        "perfecto gracias",
    }:

        # Devuelve una frase aleatoria de agradecimiento,
        # definida dentro del sistema de personalidad.
        return thank_you_response()

    # -------------------------------------------------------------------------
    # IDENTIDAD DEL ASISTENTE
    # -------------------------------------------------------------------------

    if text in {
        "quien eres",
        "como te llamas",
    }:

        # identity() necesita:
        #
        # - El nombre del asistente.
        # - El nombre del proyecto.
        return identity(
            context.atlas.get_name(),
            context.atlas.get_project(),
        )

    # -------------------------------------------------------------------------
    # INTENCIÓN NO RECONOCIDA
    # -------------------------------------------------------------------------
    #
    # None indica que este archivo no sabe responder.
    #
    # Atlas continuará con otra capa o mostrará
    # una respuesta de "no entendido".
    return None