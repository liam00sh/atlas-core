"""
===============================================================================
Proyecto Atlas
Archivo: console/command_manager.py

Descripción:
    Este módulo gestiona todos los comandos disponibles en Atlas.

    Sus responsabilidades principales son:

    1. Buscar automáticamente los módulos de la carpeta commands/.
    2. Importar cada comando encontrado.
    3. Registrar su nombre principal y sus alias.
    4. Normalizar los nombres para ignorar mayúsculas, acentos y algunas erratas.
    5. Resolver qué comando quería utilizar el usuario.
    6. Ejecutar el comando correspondiente.
    7. Informar al bucle principal de si Atlas debe continuar o cerrarse.

Ejemplo:

    El archivo:

        commands/version.py

    puede declarar:

        COMMAND = {
            "name": "version",
            "aliases": ["ver", "v"],
        }

    Este gestor registrará:

        version -> commands.version
        ver     -> commands.version
        v       -> commands.version

    De esta forma, las tres entradas ejecutarán el mismo comando.

Flujo general:

    Carpeta commands/
            │
            ▼
    load_commands()
            │
            ▼
    Diccionario COMMANDS
            │
            ▼
    resolve_command()
            │
            ▼
    execute()

===============================================================================
"""


# =============================================================================
# IMPORTACIONES DE LA BIBLIOTECA ESTÁNDAR
# =============================================================================

# importlib permite importar módulos de Python dinámicamente.
#
# Normalmente un módulo se importa escribiendo:
#
#     from commands import version
#
# Con importlib podemos construir el nombre del módulo en tiempo
# de ejecución y cargarlo automáticamente:
#
#     importlib.import_module("commands.version")
import importlib

# pkgutil permite recorrer los módulos disponibles dentro
# de un paquete de Python.
#
# En este caso lo utilizamos para buscar todos los archivos
# existentes dentro de la carpeta commands/.
import pkgutil


# =============================================================================
# IMPORTACIÓN DEL PAQUETE DE COMANDOS
# =============================================================================

# Importamos el paquete commands completo.
#
# Gracias a commands.__path__, pkgutil podrá saber en qué
# carpeta física debe buscar los módulos de comandos.
import commands


# =============================================================================
# IMPORTACIONES DE UTILIDADES DE TEXTO
# =============================================================================

# Normaliza el texto para facilitar su comparación.
#
# Dependiendo de su implementación, puede:
#
# - Convertir a minúsculas.
# - Eliminar acentos.
# - Corregir algunas erratas comunes.
# - Reducir espacios.
from utils.text_normalizer import normalize_text

# Busca la frase disponible más parecida al texto recibido.
#
# Se utiliza para aceptar pequeñas erratas en los comandos.
#
# Ejemplos:
#
#   "versoin" -> "version"
#   "aydua"   -> "ayuda"
from utils.text_normalizer import find_closest_phrase


# =============================================================================
# REGISTRO GLOBAL DE COMANDOS
# =============================================================================

# Diccionario donde se almacenarán todos los comandos descubiertos.
#
# Las claves serán los nombres o alias normalizados.
# Los valores serán los módulos de Python correspondientes.
#
# Ejemplo:
#
# COMMANDS = {
#     "version": módulo commands.version,
#     "ver": módulo commands.version,
#     "v": módulo commands.version,
#     "salir": módulo commands.exit,
# }
COMMANDS = {}


def load_commands():
    """
    Busca y carga automáticamente todos los comandos.

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        1. Recorre la carpeta commands/.
        2. Importa cada módulo encontrado.
        3. Lee su diccionario COMMAND.
        4. Registra el nombre principal.
        5. Registra todos sus alias.

    Requisito:
        Cada módulo de comando debe contener un diccionario
        llamado COMMAND.

    Ejemplo mínimo:

        COMMAND = {
            "name": "fecha",
            "aliases": ["hora"],
        }

        def execute():
            ...
    """

    # pkgutil.iter_modules() devuelve información sobre
    # los módulos encontrados dentro de commands.__path__.
    #
    # Si existen:
    #
    # commands/help.py
    # commands/version.py
    # commands/exit.py
    #
    # el bucle los recorrerá uno por uno.
    for module in pkgutil.iter_modules(
        commands.__path__
    ):

        # module.name contiene únicamente el nombre del archivo
        # sin la extensión .py.
        #
        # Ejemplo:
        #
        # "version"
        module_name = module.name

        # Importamos dinámicamente el módulo completo.
        #
        # Si module_name vale "version", se importa:
        #
        # commands.version
        command = importlib.import_module(
            f"commands.{module_name}"
        )

        # Leemos el nombre principal declarado dentro
        # del diccionario COMMAND del módulo.
        #
        # Ejemplo:
        #
        # command.COMMAND["name"] -> "version"
        #
        # Después lo normalizamos para que el registro
        # utilice una forma consistente.
        command_name = normalize_text(
            command.COMMAND["name"]
        )

        # Registramos el nombre principal y asociamos
        # ese nombre con el módulo importado.
        #
        # Ejemplo:
        #
        # COMMANDS["version"] = commands.version
        COMMANDS[command_name] = command

        # Obtenemos la lista de alias del comando.
        #
        # get("aliases", []) significa:
        #
        # - Si existe "aliases", devuelve su lista.
        # - Si no existe, devuelve una lista vacía.
        #
        # Esto evita un error KeyError cuando un comando
        # no tenga alias.
        for alias in command.COMMAND.get(
            "aliases",
            [],
        ):

            # Normalizamos también cada alias.
            normalized_alias = normalize_text(
                alias
            )

            # Registramos el alias apuntando al mismo módulo.
            #
            # Ejemplo:
            #
            # COMMANDS["ver"] = commands.version
            COMMANDS[normalized_alias] = command


# Ejecutamos la carga automática al importar este archivo.
#
# Esto significa que COMMANDS estará preparado antes
# de que Atlas comience a procesar entradas.
load_commands()


def resolve_command(
    command_name: str,
) -> str | None:
    """
    Intenta identificar un comando escrito por el usuario.

    Parámetros:
        command_name:
            Texto que podría representar un comando.

    Devuelve:
        str:
            Nombre normalizado del comando encontrado.

        None:
            No se ha encontrado ninguna coincidencia válida.

    Ejemplos:

        resolve_command("version")
            -> "version"

        resolve_command("VERSIÓN")
            -> "version"

        resolve_command("versoin")
            -> "version"

        resolve_command("qué sabes de Saray")
            -> None
    """

    # Normalizamos la entrada del usuario.
    #
    # COMMANDS.keys() se pasa como vocabulario adicional
    # para ayudar al corrector a reconocer nombres y alias
    # existentes.
    normalized_name = normalize_text(
        command_name,
        COMMANDS.keys(),
    )

    # Primero comprobamos si existe una coincidencia exacta.
    #
    # Esto cubre:
    #
    # - El nombre principal.
    # - Un alias.
    # - Una entrada que haya quedado igual tras normalizarse.
    if normalized_name in COMMANDS:
        return normalized_name

    # -------------------------------------------------------------------------
    # PROTECCIÓN CONTRA FALSOS POSITIVOS
    # -------------------------------------------------------------------------
    #
    # No queremos interpretar frases largas como comandos
    # mediante similitud aproximada.
    #
    # Por ejemplo:
    #
    # "que sabea de saray"
    #
    # no debería convertirse accidentalmente en:
    #
    # "ayuda"
    #
    # Por eso solo intentamos la búsqueda aproximada
    # cuando la entrada tiene tres palabras o menos.
    if len(normalized_name.split()) > 3:
        return None

    # Buscamos el nombre o alias más parecido.
    #
    # cutoff=0.84 indica que la similitud debe ser
    # como mínimo del 84 %.
    #
    # Un valor alto reduce las interpretaciones erróneas.
    return find_closest_phrase(
        text=normalized_name,
        candidates=COMMANDS.keys(),
        cutoff=0.84,
    )


def execute(command_name):
    """
    Resuelve y ejecuta un comando.

    Parámetros:
        command_name:
            Nombre, alias o variante aproximada del comando.

    Devuelve:
        True:
            Atlas debe continuar funcionando.

        False:
            Atlas debe cerrarse.

    Los comandos normales suelen devolver None.
    En ese caso, este gestor lo convierte en True.

    Un comando como "salir" puede devolver False
    para finalizar el bucle de la consola.
    """

    # Intentamos identificar el comando solicitado.
    resolved_name = resolve_command(
        command_name
    )

    # Si no se encuentra ninguna coincidencia válida,
    # informamos al usuario.
    if resolved_name is None:

        print()

        print("No conozco ese comando.")

        print(
            "Escribe «ayuda» para ver "
            "los disponibles."
        )

        # Atlas continúa funcionando aunque el comando
        # no haya sido reconocido.
        return True

    # Recuperamos el módulo asociado al nombre resuelto.
    #
    # Ejemplo:
    #
    # resolved_name = "version"
    #
    # command = commands.version
    command = COMMANDS[
        resolved_name
    ]

    # Ejecutamos la función execute() definida dentro
    # del módulo correspondiente.
    #
    # Ejemplo:
    #
    # commands.version.execute()
    result = command.execute()

    # La mayoría de comandos no necesita controlar
    # el cierre del programa y devuelve None.
    #
    # Interpretamos None como:
    #
    # "Continuar ejecutando Atlas".
    if result is None:
        return True

    # Si el comando devuelve explícitamente True o False,
    # respetamos ese resultado.
    #
    # Por ejemplo:
    #
    # True  -> un invitado se despide, pero Atlas continúa.
    # False -> Liam ejecuta "salir" y Atlas se cierra.
    return result