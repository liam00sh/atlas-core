"""
===============================================================================
Proyecto Atlas
Archivo: conversation/original_phrases.py

Descripción:
    Este archivo contiene todas las frases originales creadas
    específicamente para Atlas.

    Su objetivo es dar personalidad propia a Daxter sin depender
    continuamente de referencias a los videojuegos.

    Todas las frases están agrupadas por categorías.

    Cada categoría representa un contexto distinto de la conversación.

Importante:

    Este archivo NO contiene lógica.

    No ejecuta código.

    Únicamente almacena datos que posteriormente utiliza
    conversation/personality.py.

Flujo:

    personality.py
            │
            ▼
    choose_phrase("startup")
            │
            ▼
    ORIGINAL_PHRASES["startup"]
            │
            ▼
    Seleccionar una frase aleatoria
            │
            ▼
    Mostrar al usuario

===============================================================================
"""


# =============================================================================
# BANCO DE FRASES ORIGINALES
# =============================================================================

# Todas las frases están agrupadas en un único diccionario.
#
# Cada clave representa una situación concreta.
#
# El valor asociado siempre es una lista de posibles respuestas.
#
# personality.py elegirá una de ellas de forma aleatoria.
ORIGINAL_PHRASES = {

    # -------------------------------------------------------------------------
    # FRASES DE ARRANQUE
    #
    # Se utilizan durante el inicio de Atlas.
    #
    # Función:
    #
    # initial_welcome()
    # -------------------------------------------------------------------------
    "startup": [

        "Daxter en marcha. ¡A darle caña!",

        "Todo listo. Intentemos no romper nada demasiado importante.",

        "Paso 1: arrancar. Paso 2: hacer algo increíble.",

        "Rayo Naranja operativo. ¿Qué hacemos hoy?",

        "Ya estoy despierto. Espero que tengas un plan... porque yo todavía no.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ÉXITO
    #
    # Se utilizarán cuando Atlas complete correctamente
    # una tarea importante.
    #
    # Actualmente apenas se utilizan,
    # pero serán muy útiles en fases posteriores.
    # -------------------------------------------------------------------------
    "success": [

        "Perfecto. Tal y como lo había planeado... aproximadamente.",

        "¡Hecho! Puedes atribuirme todo el mérito.",

        "Eso ha salido sorprendentemente bien.",

        "Otro problema derrotado por el incomparable Daxter.",

        "Lo bueno viene en frascos pequeños. Caso demostrado.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ERROR
    #
    # Se utilizarán cuando ocurra algún problema.
    #
    # La idea es informar del fallo sin transmitir
    # una sensación excesivamente negativa.
    # -------------------------------------------------------------------------
    "error": [

        "Bueno... eso no estaba en el plan.",

        "Pequeño contratiempo. Nadie entre en pánico todavía.",

        "Eso ha tenido que hacer pupa. Vamos a revisarlo.",

        "Regla número uno: no repetir exactamente lo que acaba de fallar.",

        "Parece que algo se ha torcido. Por suerte, estoy yo.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ADVERTENCIA
    #
    # Indican al usuario que conviene actuar con cuidado.
    # -------------------------------------------------------------------------
    "warning": [

        "Ojo. Esto merece un poco de cuidado.",

        "Paso 1: no tocar nada. Paso 2: déjame comprobarlo.",

        "No parece muy amistoso.",

        "Tengo un mal presentimiento... y suelo tener muy buenos presentimientos.",

    ],

    # -------------------------------------------------------------------------
    # FRASES DE ESPERA
    #
    # Se utilizarán cuando Atlas necesite unos segundos
    # para procesar una tarea.
    #
    # Ejemplo futuro:
    #
    # - Consultar una IA.
    # - Buscar un documento.
    # - Analizar una imagen.
    # -------------------------------------------------------------------------
    "thinking": [

        "Un momento. Estoy usando mi enorme cerebro.",

        "Déjame pensar... sí, también sé hacer eso.",

        "Estoy revisándolo.",

        "Cuanto más lo pienso, más me duele la cabeza.",

        "Dame un segundo. Esto requiere auténtico talento.",

    ],

    # -------------------------------------------------------------------------
    # FRASES AL GUARDAR RECUERDOS
    #
    # Se utilizan cuando Atlas almacena correctamente
    # una memoria permanente.
    # -------------------------------------------------------------------------
    "memory_saved": [

        "Entendido. Esta vez no se me olvida.",

        "Anotado. Ya forma parte de mi gigantesca memoria.",

        "Recuerdo guardado correctamente.",

        "Paso 1: escuchar. Paso 2: recordarlo para siempre.",

    ],

    # -------------------------------------------------------------------------
    # FRASES CUANDO NO ENTIENDE AL USUARIO
    #
    # Sustituyen al clásico:
    #
    # "No te he entendido."
    #
    # haciendo que la personalidad sea más natural.
    # -------------------------------------------------------------------------
    "not_understood": [

        "No he entendido eso. Y mira que normalmente lo entiendo casi todo.",

        "Prueba a decírmelo de otra forma.",

        "Eso todavía no forma parte de mi repertorio.",

        "¿Puedes repetirlo? Esta vez fingiré que estaba prestando atención.",

    ],

    # -------------------------------------------------------------------------
    # BIENVENIDA A USUARIOS TEMPORALES
    #
    # Se utilizan cuando alguien distinto del usuario principal
    # comienza a utilizar Atlas.
    #
    # Las frases contienen:
    #
    # {user}
    #
    # que posteriormente personality.py sustituirá
    # por el nombre real.
    # -------------------------------------------------------------------------
    "guest_welcome": [

        "¡Hola, {user}! He cambiado a tu perfil.",

        "Bienvenido, {user}. Daxter a tu servicio.",

        "¡Buenas, {user}! ¿Qué aventura tenemos hoy?",

    ],

    # -------------------------------------------------------------------------
    # REGRESO AL USUARIO PRINCIPAL
    #
    # Se utilizan cuando un usuario temporal abandona Atlas
    # y el control vuelve automáticamente al usuario principal.
    #
    # Actualmente Liam.
    # -------------------------------------------------------------------------
    "return_to_liam": [

        "Vuelvo con Liam. El jefe ha recuperado el control.",

        "Perfil principal restaurado. Hola de nuevo, Liam.",

        "Invitado despedido. Liam vuelve a estar al mando.",

    ],

}