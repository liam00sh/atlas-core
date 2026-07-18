"""
===============================================================================
Proyecto Atlas
Archivo: commands/exit.py

Descripción:
    Implementa el comando "salir".

    Este comando tiene dos comportamientos distintos dependiendo del usuario
    que esté utilizando Atlas:

    • Usuario principal (Liam)
        → Atlas finaliza completamente.

    • Usuario temporal (Saray, Lidia, etc.)
        → Atlas no se cierra.
        → Se despide del usuario temporal.
        → Vuelve automáticamente al usuario principal.

¿Por qué funciona así?

    Atlas está pensado como un asistente compartido dentro de casa.

    Los invitados pueden utilizarlo temporalmente, pero cuando terminan
    simplemente abandonan su sesión sin apagar completamente el asistente.

Flujo:

            salir
              │
              ▼
     ¿Es usuario principal?
          │          │
         Sí          No
          │          │
          ▼          ▼
  Despedida final   Despedida temporal
          │          │
          ▼          ▼
   return False   Volver a Liam
                     │
                     ▼
                return True
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Función que genera la despedida definitiva cuando Atlas va a cerrarse.
from conversation.personality import final_goodbye

# Función que genera la despedida de un usuario temporal y el regreso
# automático al usuario principal.

# Importamos el contexto global para acceder a la única instancia de Atlas
# creada en main.py.
from core import context


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

# Todos los comandos de Atlas incluyen un diccionario COMMAND con la
# información necesaria para que command_manager.py pueda registrarlos
# automáticamente.
COMMAND = {

    # Nombre principal del comando.
    "name": "salir",

    # Descripción que aparecerá en el comando "ayuda".
    "description": "Finaliza Atlas o cierra el perfil temporal.",

    # Categoría a la que pertenece.
    "category": "Sistema",

    # Autor del comando.
    "author": "Liam",

    # Versión del propio comando.
    "version": "1.1",

    # Alias aceptados.
    #
    # Todos ejecutarán exactamente la misma función.
    "aliases": [

        "exit",

        "quit",

        "adios",

        "adiós",

        "hasta luego",

    ],

    # Ejemplos mostrados en futuras ayudas o documentación.
    "examples": [

        "salir",

        "adios",

    ],

}


def execute():
    """
    Ejecuta el comando "salir".

    No recibe parámetros.

    Devuelve:

        True
            Atlas continúa funcionando.

        False
            Atlas debe finalizar.

    Funcionamiento:

        Si el usuario actual NO es Liam:

            • Se despide del usuario.
            • Se vuelve automáticamente al usuario principal.
            • Atlas continúa funcionando.

        Si el usuario actual es Liam:

            • Se muestra la despedida final.
            • Atlas indica que debe cerrarse.
    """

    # -------------------------------------------------------------------------
    # Obtenemos el nombre del usuario que está utilizando Atlas
    # en este momento.
    #
    # Ejemplo:
    #
    # Liam
    # Saray
    # Lidia
    # -------------------------------------------------------------------------
    current_user = context.atlas.get_user()

    print()

    # -------------------------------------------------------------------------
    # CASO 1
    #
    # El usuario NO es el principal.
    #
    # En este caso Atlas no se apaga.
    #
    # Simplemente finaliza la sesión temporal y vuelve automáticamente
    # al usuario principal.
    # -------------------------------------------------------------------------
    if not context.atlas.is_main_user():

        # Obtenemos el nombre del usuario principal.
        #
        # Actualmente será Liam.
        main_user = context.atlas.get_main_user()

        # Cerramos el perfil temporal sin simular una nueva bienvenida.
        # Atlas restaura internamente al usuario principal, pero no inicia
        # una conversación nueva ni anuncia a Liam si nadie ha hablado.
        print(f"Adiós, {current_user}. Perfil temporal cerrado.")

        context.atlas.return_to_main_user()

        # True indica al shell que Atlas debe seguir funcionando.
        return True

    # -------------------------------------------------------------------------
    # CASO 2
    #
    # El usuario actual es el principal.
    #
    # Ahora sí finalizamos completamente Atlas.
    # -------------------------------------------------------------------------
    print(

        final_goodbye(
            current_user
        )

    )

    # False rompe el bucle principal del shell.
    #
    # shell.py:
    #
    # running = atlas.process(...)
    #
    # while running:
    #
    # Cuando running pasa a valer False,
    # la consola termina y el programa finaliza.
    return False