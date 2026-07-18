"""Detección de intenciones conversacionales sencillas."""


from assistant_identity.phrase_bank import IDENTITY_CHANGED
from conversation.personality import greet, identity, thank_you_response, user_changed
from core import context
from utils.text_normalizer import normalize_text




def _change_to_declared_user(user: str) -> str:
    clean_user = str(user).strip().title()


    if not clean_user:
        return "No he entendido el nombre del usuario."


    atlas = context.atlas
    people_manager = getattr(atlas, "people_manager", None)


    if people_manager is not None:
        animal = people_manager.find_animal_by_name(clean_user)


        if animal is not None:
            preferred_name = (
                animal.aliases[0]
                if getattr(animal, "aliases", [])
                else animal.name
            )
            return (
                f"{preferred_name} es un animal y no puede tener perfil "
                "de usuario ni hablar con Atlas. Sigues siendo "
                f"{atlas.get_user()}."
            )


        person = people_manager.find_person_by_name(clean_user)


        if person is not None and person.user_profile:
            clean_user = person.user_profile


    current_user = str(atlas.get_user()).strip()
    if current_user.casefold() == clean_user.casefold():
        import random
        return random.choice((
            f"Ya estás usando el perfil de {current_user}.",
            f"Sigues siendo {current_user}; no hace falta cambiar de perfil.",
            f"El perfil activo ya es {current_user}.",
        ))

    changed = atlas.change_user(clean_user)


    if changed is False:
        return (
            f"No se ha podido cambiar al perfil de {clean_user}. "
            f"El usuario activo sigue siendo {atlas.get_user()}."
        )


    return user_changed(clean_user, atlas.get_name())




def _change_assistant_identity(identity_name: str) -> str:
    """Cambia la identidad activa sin enviar la petición fallida a la IA."""


    atlas = context.atlas
    active_before = atlas.identity_manager.get_active_display_name()

    if active_before.casefold() == str(identity_name).casefold():
        import random
        messages = {
            "daxter": (
                "Ya soy Daxter. Has fallado el cambio más fácil del día.",
                "Daxter ya estaba aquí. Otra vez será, pringado.",
                "Cambiar de Daxter a Daxter: cero progreso, bastante estilo.",
            ),
            "coco": (
                "Ya soy Coco. El sistema confirma que no hacía falta tocar nada.",
                "Coco ya estaba activa. Operación completada con exactamente cero cambios.",
                "Has pedido a Coco mientras hablaba Coco. Técnicamente impecable, estratégicamente inútil.",
            ),
        }
        return random.choice(messages.get(str(identity_name).casefold(), (f"Ya está activa {active_before}.",)))

    changed = atlas.identity_manager.change_identity(identity_name)


    if not changed:
        return f"No existe ninguna identidad llamada {identity_name}."


    active_name = atlas.identity_manager.get_active_display_name()


    return atlas.identity_manager.get_phrase(
        category=IDENTITY_CHANGED,
        default=f"Identidad activa: {active_name}.",
        user=atlas.get_user(),
    )





def _acknowledgement_expected() -> bool:
    """Indica si una respuesta breve parece continuar una intervención previa."""

    atlas = context.atlas
    try:
        messages = atlas.get_current_ai_context().get_messages()
    except (AttributeError, TypeError):
        return False

    if not messages:
        return False

    last = messages[-1]
    content = str(last.get("content", "") if isinstance(last, dict) else "")
    role = last.get("role") if isinstance(last, dict) else None
    return role == "assistant" and bool(content.strip())


def _short_acknowledgement(normalized: str) -> str:
    """Responde a confirmaciones breves sin tratarlas siempre igual."""

    import random

    expected = _acknowledgement_expected()
    assistant = context.atlas.get_name()
    name = assistant.casefold()

    if normalized in {"gracias", "muchas gracias", "te lo agradezco", "perfecto gracias"}:
        return thank_you_response(assistant, expected=expected)

    if expected:
        if name == "coco":
            messages = (
                "Perfecto. Queda entendido y seguimos.",
                "Anotado. Continuamos sin convertirlo en una ceremonia.",
                "Vale, dato recibido. El plan sigue en marcha.",
                "Genial. Una confirmación limpia y sin errores de sintaxis.",
                "Entendido. Siguiente paso cuando toque.",
            )
        else:
            messages = (
                "Vale, entendido. La misión continúa.",
                "Genial. Eso suena peligrosamente parecido a un plan.",
                "Perfecto. Lo aceptaré como aprobación oficial del héroe.",
                "Recibido. Paso siguiente antes de que aparezcan pinchos.",
                "De acuerdo. Todo bajo control, o al menos bien disimulado.",
            )
    else:
        if name == "coco":
            messages = (
                "¿Vale... a qué exactamente? Me falta una variable en esa ecuación.",
                "Genial, supongo. El contexto ha decidido tomarse el día libre.",
                "Confirmación recibida sin pregunta asociada. Curioso, pero válido.",
                "¿De nada? Hemos empezado la conversación por el epílogo.",
            )
        else:
            messages = (
                "¿Vale qué? ¿He aprobado una misión sin enterarme?",
                "Genial... aunque no sé qué celebramos. Yo me apunto.",
                "Eso ha sonado a respuesta de una conversación paralela.",
                "¿De nada? Vaya, me he perdido la parte donde hacía algo heroico.",
            )

    return random.choice(messages)

def detect(text: str) -> str | None:
    normalized = normalize_text(text)


    user_prefixes = (
        "hola soy ",
        "me llamo ",
        "ahora soy ",
        "identificame como ",
        "identificarme como ",
        "cambia de usuario a ",
        "cambiar de usuario a ",
        "cambia usuario a ",
        "cambiar usuario a ",
        "soy ",
    )


    for prefix in user_prefixes:
        if normalized.startswith(prefix):
            declared_user = normalized[len(prefix):].strip()
            return _change_to_declared_user(declared_user)


    identity_commands = {
        "cambia a coco": "coco",
        "cambiar a coco": "coco",
        "pon a coco": "coco",
        "ponme a coco": "coco",
        "cambia a daxter": "daxter",
        "cambiar a daxter": "daxter",
        "pon a daxter": "daxter",
        "ponme a daxter": "daxter",
    }


    identity_name = identity_commands.get(normalized)


    if identity_name is not None:
        return _change_assistant_identity(identity_name)


    if normalized in {
        "hola",
        "buenas",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
    }:
        return greet(
            context.atlas.get_user(),
            context.atlas.get_name(),
        )


    if normalized in {
        "gracias",
        "muchas gracias",
        "te lo agradezco",
        "perfecto gracias",
        "vale",
        "ok",
        "okay",
        "genial",
        "perfecto",
        "de acuerdo",
        "de nada",
    }:
        return _short_acknowledgement(normalized)


    if normalized in {"quien eres", "como te llamas", "presentate", "presentate por favor"}:
        return identity(
            context.atlas.get_name(),
            context.atlas.get_project(),
        )


    return None