"""
===============================================================================
Proyecto Atlas
Archivo: conversation/responses.py

Descripción:
    Este archivo contiene respuestas simples organizadas por palabras clave.

    Fue uno de los primeros sistemas de conversación de Atlas.

    Actualmente gran parte de estas respuestas han sido sustituidas por
    conversation/personality.py, que genera respuestas más naturales,
    dinámicas y con personalidad.

Estado actual:
    Archivo heredado.

    Se mantiene por compatibilidad y porque algunas respuestas podrían
    reutilizarse en el futuro.

Posible evolución:

    En futuras versiones podría desaparecer completamente,
    integrándose todo dentro de:

        personality.py

    o incluso ser reemplazado por una IA local.

===============================================================================
"""


# =============================================================================
# RESPUESTAS BÁSICAS
# =============================================================================

# Cada clave representa una posible entrada del usuario.
#
# El valor asociado es una lista de respuestas posibles.
#
# Si varias respuestas están disponibles,
# el sistema puede elegir una aleatoriamente.
RESPONSES = {

    # -------------------------------------------------------------------------
    # SALUDOS
    #
    # Respuestas sencillas cuando el usuario saluda.
    # -------------------------------------------------------------------------
    "hola": [

        "Hola Liam.",

        "¡Hola Liam!",

        "Hola, ¿qué tal?"

    ],

    # -------------------------------------------------------------------------
    # DESPEDIDAS
    #
    # Se utilizan cuando el usuario se despide.
    # Actualmente la salida principal del programa
    # se gestiona mediante el comando "salir".
    # -------------------------------------------------------------------------
    "adios": [

        "Hasta luego.",

        "Nos vemos.",

        "Que tengas un buen día."

    ],

    # -------------------------------------------------------------------------
    # AGRADECIMIENTOS
    #
    # Respuestas sencillas cuando el usuario da las gracias.
    # -------------------------------------------------------------------------
    "gracias": [

        "De nada.",

        "Para eso estoy.",

        "Siempre que quieras."

    ],

    # -------------------------------------------------------------------------
    # IDENTIDAD
    #
    # Pequeña descripción del asistente.
    #
    # Actualmente esta información también puede generarse desde
    # personality.py mediante funciones más completas.
    # -------------------------------------------------------------------------
    "quien eres": [

        "Soy Daxter, el asistente del Proyecto Atlas."

    ]

}