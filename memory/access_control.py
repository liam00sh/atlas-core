"""
===============================================================================
Proyecto Atlas
Archivo: memory/access_control.py

Descripción:
    Este módulo controla los permisos de lectura de la memoria de Atlas.

    Su función principal es decidir si un usuario puede consultar
    un recuerdo concreto.

    La decisión depende de:

    - Quién es el propietario del recuerdo.
    - Quién intenta consultarlo.
    - El perfil del usuario que consulta.
    - Sus roles.
    - Sus relaciones con el propietario.
    - El nivel de visibilidad del recuerdo.

Ejemplo:

    Recuerdo:
        Propietario: Liam
        Visibilidad: partner

    Usuario que consulta:
        Saray

    Perfil de Saray:
        partner_of: ["Liam"]

    Resultado:
        True

Importante:
    Este módulo no guarda recuerdos ni perfiles.

    Solo responde:

        True  -> Puede leerlo.
        False -> No puede leerlo.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES DE NIVELES DE VISIBILIDAD
# =============================================================================

# Información que puede consultar el propietario del recuerdo
# y un usuario con rol de administrador.
from memory.visibility import ADMIN_MANAGED

# Información destinada a familiares autorizados.
from memory.visibility import FAMILY

# Información accesible para personas conocidas o de confianza.
from memory.visibility import KNOWN

# Información accesible para la pareja autorizada.
from memory.visibility import PARTNER

# Información privada.
from memory.visibility import PRIVATE

# Información pública.
from memory.visibility import PUBLIC


def _normalize(value: str) -> str:
    """
    Normaliza un texto para compararlo.

    Parámetros:
        value:
            Texto que se desea normalizar.

    Devuelve:
        str:
            Texto sin espacios exteriores y en minúsculas.

    Ejemplo:
        "  Liam  " -> "liam"

    El guion bajo inicial indica que esta función está pensada
    para uso interno dentro de este módulo.
    """

    return value.strip().lower()


def _has_role(
    profile: dict,
    role: str,
) -> bool:
    """
    Comprueba si un perfil tiene un rol concreto.

    Parámetros:
        profile:
            Diccionario con la información del usuario.

        role:
            Rol que se desea comprobar.

    Devuelve:
        True:
            El perfil contiene ese rol.

        False:
            El perfil no lo contiene.

    Ejemplo:
        profile["roles"] = ["owner", "admin"]

        _has_role(profile, "admin")
            -> True
    """

    # profile.get("roles", []) significa:
    #
    # - Si existe la clave "roles", devuelve su lista.
    # - Si no existe, devuelve una lista vacía.
    #
    # Esto evita un error KeyError.
    return role in profile.get(
        "roles",
        [],
    )


def _has_relationship(
    viewer_profile: dict,
    relationship: str,
    owner: str,
) -> bool:
    """
    Comprueba si el usuario que consulta tiene una relación
    concreta con el propietario del recuerdo.

    Parámetros:
        viewer_profile:
            Perfil del usuario que intenta consultar la memoria.

        relationship:
            Tipo de relación que se desea comprobar.

            Ejemplos:
                "partner_of"
                "family_of"
                "known_of"

        owner:
            Propietario del recuerdo.

    Devuelve:
        True:
            Existe la relación.

        False:
            No existe.

    Ejemplo:
        Saray tiene:

            "partner_of": ["Liam"]

        Entonces:

            _has_relationship(
                perfil_saray,
                "partner_of",
                "Liam",
            )

        devuelve True.
    """

    # Obtenemos la lista de personas asociadas
    # a la relación solicitada.
    #
    # Primero:
    #
    # viewer_profile.get("relationships", {})
    #
    # devuelve el diccionario de relaciones.
    #
    # Después:
    #
    # .get(relationship, [])
    #
    # obtiene la lista correspondiente.
    related_users = viewer_profile.get(
        "relationships",
        {},
    ).get(
        relationship,
        [],
    )

    # Normalizamos el nombre del propietario.
    normalized_owner = _normalize(owner)

    # any() devuelve True si al menos una persona
    # de la lista coincide con el propietario.
    return any(
        _normalize(user) == normalized_owner
        for user in related_users
    )


def can_read_memory(
    memory: dict,
    viewer: str,
    viewer_profile: dict,
) -> bool:
    """
    Decide si un usuario puede leer un recuerdo.

    Parámetros:
        memory:
            Recuerdo que se desea consultar.

            Debe contener al menos:

                {
                    "owner": "Liam",
                    "visibility": "partner"
                }

        viewer:
            Nombre de la persona que intenta leerlo.

        viewer_profile:
            Perfil completo de esa persona.

    Devuelve:
        True:
            El usuario tiene permiso.

        False:
            El acceso está denegado.

    Orden de prioridad:

        1. Propietario general del sistema.
        2. Propietario del recuerdo.
        3. Recuerdo privado.
        4. Recuerdo público.
        5. Información administrativa.
        6. Pareja.
        7. Familia.
        8. Personas conocidas.
        9. Denegar por defecto.
    """

    # Propietario del recuerdo.
    owner = memory["owner"]

    # Nivel de privacidad.
    visibility = memory["visibility"]

    # -------------------------------------------------------------------------
    # 1. PROPIETARIO GENERAL DEL SISTEMA
    # -------------------------------------------------------------------------
    #
    # Un perfil con rol "owner" puede consultar
    # toda la memoria gestionada por Atlas.
    #
    # Actualmente Liam tiene ese rol.
    if _has_role(
        viewer_profile,
        "owner",
    ):
        return True

    # -------------------------------------------------------------------------
    # 2. PROPIETARIO DEL RECUERDO
    # -------------------------------------------------------------------------
    #
    # Cada persona puede consultar sus propios recuerdos,
    # independientemente de su nivel de privacidad.
    if _normalize(viewer) == _normalize(owner):
        return True

    # -------------------------------------------------------------------------
    # 3. RECUERDO PRIVADO
    # -------------------------------------------------------------------------
    #
    # Si no se ha concedido acceso anteriormente,
    # un recuerdo privado queda bloqueado.
    #
    # El owner general ya habría recibido True
    # en el primer bloque.
    if visibility == PRIVATE:
        return False

    # -------------------------------------------------------------------------
    # 4. RECUERDO PÚBLICO
    # -------------------------------------------------------------------------
    #
    # Cualquier usuario puede consultarlo.
    if visibility == PUBLIC:
        return True

    # -------------------------------------------------------------------------
    # 5. INFORMACIÓN ADMINISTRATIVA
    # -------------------------------------------------------------------------
    #
    # Puede verla quien tenga el rol "admin".
    if visibility == ADMIN_MANAGED:
        return _has_role(
            viewer_profile,
            "admin",
        )

    # -------------------------------------------------------------------------
    # 6. INFORMACIÓN DE PAREJA
    # -------------------------------------------------------------------------
    #
    # Se permite si el usuario que consulta
    # aparece como pareja del propietario.
    if visibility == PARTNER:
        return _has_relationship(
            viewer_profile,
            "partner_of",
            owner,
        )

    # -------------------------------------------------------------------------
    # 7. INFORMACIÓN FAMILIAR
    # -------------------------------------------------------------------------
    #
    # Se permite si el usuario aparece como familiar
    # del propietario.
    if visibility == FAMILY:
        return _has_relationship(
            viewer_profile,
            "family_of",
            owner,
        )

    # -------------------------------------------------------------------------
    # 8. INFORMACIÓN PARA PERSONAS DE CONFIANZA
    # -------------------------------------------------------------------------
    #
    # Puede leerla una persona que sea:
    #
    # - Pareja.
    # - Familia.
    # - Conocida o de confianza.
    if visibility == KNOWN:
        return any(
            (
                _has_relationship(
                    viewer_profile,
                    "partner_of",
                    owner,
                ),

                _has_relationship(
                    viewer_profile,
                    "family_of",
                    owner,
                ),

                _has_relationship(
                    viewer_profile,
                    "known_of",
                    owner,
                ),
            )
        )

    # -------------------------------------------------------------------------
    # 9. DENEGAR POR DEFECTO
    # -------------------------------------------------------------------------
    #
    # Si aparece un nivel desconocido o mal escrito,
    # no concedemos acceso.
    #
    # Esta es una política segura:
    #
    # Ante la duda, denegar.
    return False