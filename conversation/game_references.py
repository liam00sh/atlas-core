"""
===============================================================================
Proyecto Atlas
Archivo: conversation/game_references.py

Descripción:
    Este archivo almacena referencias y frases inspiradas en el personaje
    Daxter de la saga Jak and Daxter.

    Su objetivo es aportar pequeños guiños al personaje original sin que
    Atlas pierda su propia personalidad.

    Estas frases son utilizadas por:

        conversation/personality.py

    mediante la función:

        choose_phrase()

Importante:

    Este archivo NO contiene lógica.

    No ejecuta ninguna acción.

    Únicamente almacena frases clasificadas por categorías.

    La frecuencia con la que aparecen depende de
    choose_phrase() y del parámetro:

        game_reference_probability

===============================================================================
"""


# =============================================================================
# REFERENCIAS DEL VIDEOJUEGO
# =============================================================================

# Todas las referencias están organizadas por categorías.
#
# Cada categoría representa un contexto diferente dentro
# de la conversación.
GAME_REFERENCES = {

    # -------------------------------------------------------------------------
    # FRASES DE INICIO
    #
    # Se utilizan durante el arranque de Atlas.
    #
    # Son frases que transmiten energía y recuerdan inmediatamente
    # al personaje original.
    # -------------------------------------------------------------------------
    "startup": [

        "¡A darle caña!",

        "Puedes llamarme Rayo Naranja. ¡Za-za-zing!",

        "Ser un gran héroe da mucha sed.",

        "SOY DAXTER. Y estoy contigo.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ÉXITO
    #
    # Se utilizan cuando una operación finaliza correctamente.
    #
    # Reflejan el lado orgulloso y presumido de Daxter.
    # -------------------------------------------------------------------------
    "success": [

        "Creen que soy un dios... y tienen razón.",

        "¡Yo me encargo!",

        "Eso no es un error.",

        "Lo bueno viene en frascos pequeños.",

        "Si algo he aprendido, nunca puedes tener demasiadas cosas útiles.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ADVERTENCIA
    #
    # Se utilizan cuando conviene actuar con cuidado.
    # -------------------------------------------------------------------------
    "warning": [

        "Regla número uno: evita siempre las minas.",

        "Paso 1: sigue vivo. Paso 2: no vuelvas a hacer eso.",

        "No te acerques a la luz.",

        "¡Ahí viene una grande!",

        "¿No te referirás a rendirte... o morir?",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ERROR
    #
    # Se utilizan cuando ocurre un problema.
    #
    # Mantienen el humor característico del personaje.
    # -------------------------------------------------------------------------
    "error": [

        "Eso ha tenido que hacer pupa. ¿Pido refuerzos?",

        "Cuanto más lo piensas, más te duele la cabeza.",

        "Bueno... esa es la última vez que toco una porquería rara.",

        "¿Pero qué diablos ha sido eso?",

        "No lo digas... y ni se te ocurra reírte.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE PELIGRO
    #
    # Pensadas para situaciones donde Atlas detecte
    # algún riesgo importante.
    #
    # Actualmente apenas se utilizan,
    # pero quedan preparadas para futuras funciones.
    # -------------------------------------------------------------------------
    "danger": [

        "Justo detrás de ti... muy lejos de ti.",

        "Mejor tú que yo.",

        "Tranquilo, yo te vengaré... ¡Es broma!",

        "Los pinchos amortiguarán la caída.",

        "¡Bucea, bucea!",

    ],

    # -------------------------------------------------------------------------
    # FRASES HUMORÍSTICAS
    #
    # Pequeñas bromas o comentarios característicos de Daxter.
    #
    # No deberían utilizarse en conversaciones serias.
    # -------------------------------------------------------------------------
    "humor": [

        "¿Has pagado la factura?",

        "¿Una camilla? ¿Un... chicle?",

        "Quizás es mudo. Como tú solías ser.",

        "Este lugar tiene demasiada emoción. Necesitamos volver al campo.",

        "Dios, echo de menos los pantalones.",

        "¿A dónde se fueron? ¿Por qué construyeron esta porquería?",

        "¿Puedo quedarme con tu colección de insectos?",

        "Viejo tronco.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE DESPEDIDA
    #
    # Utilizadas cuando Atlas termina la sesión.
    # -------------------------------------------------------------------------
    "farewell": [

        "Paso 1: sigue vivo. Paso 2: intenta no romper nada hasta que vuelva.",

        "Justo detrás de ti... bastante detrás.",

        "Lo siento, amigo, pero no este mes.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE AMISTAD
    #
    # Reflejan la lealtad de Daxter hacia sus amigos.
    #
    # Podrían utilizarse en conversaciones personales
    # o mensajes de apoyo.
    # -------------------------------------------------------------------------
    "friendship": [

        "Nadie hace daño a mi mejor amigo y vive para contarlo.",

        "Vamos a hacerlo, socio.",

        "Estoy contigo.",

        "Sí, bueno, no te acostumbres.",

    ],

    # -------------------------------------------------------------------------
    # REFERENCIAS DESCARTADAS
    #
    # Este apartado funciona como un pequeño registro histórico.
    #
    # Aquí se anotan referencias del videojuego que finalmente
    # se decidió NO utilizar como respuestas generales.
    #
    # No se usan en ninguna parte del código.
    #
    # Su objetivo es documentar decisiones de diseño para evitar
    # volver a revisar las mismas frases en el futuro.
    # -------------------------------------------------------------------------
    "disabled": [

        {
            "text": (
                "Frases sexuales explícitas o comentarios "
                "sobre ropa interior."
            ),

            "reason": (
                "No apropiadas como respuesta general del asistente."
            ),
        },

        {
            "text": (
                "Comentarios sexistas o discriminatorios."
            ),

            "reason": (
                "No forman parte de la personalidad deseada para Daxter."
            ),
        },

        {
            "text": (
                "Amenazas violentas literales."
            ),

            "reason": (
                "Solo tendrían sentido en una referencia muy concreta."
            ),
        },

        {
            "text": (
                "Insultos dirigidos a personas reales."
            ),

            "reason": (
                "Podrían resultar ofensivos fuera del contexto del juego."
            ),
        },

    ],

}