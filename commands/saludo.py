"""Comando de saludo dinámico del Proyecto Atlas."""


from assistant_identity.phrase_bank import GREETINGS


COMMAND = {
    "name": "saludo",
    "description": "Saluda al usuario.",
    "category": "General",
    "author": "Liam",
    "version": "1.1",
    "aliases": ["hola", "saludar", "buenas", "hey"],
    "examples": ["saludo", "hola", "buenas"],
}




def _find_atlas_context():
    """Busca la instancia de Atlas en la pila de llamadas."""


    import inspect


    frame = inspect.currentframe()


    try:
        frame = frame.f_back if frame is not None else None


        while frame is not None:
            atlas = frame.f_locals.get("self")


            if (
                atlas is not None
                and callable(getattr(atlas, "get_user", None))
                and hasattr(atlas, "identity_manager")
            ):
                return atlas


            frame = frame.f_back


    finally:
        del frame


    return None




def execute(
    user_name: str | None = None,
    assistant_name: str | None = None,
):
    """Muestra un saludo propio de la identidad activa."""


    atlas = _find_atlas_context()


    if atlas is not None:
        user_name = user_name or atlas.get_user()
        phrase = atlas.identity_manager.get_phrase(
            GREETINGS,
            default="¡Buenas! ¿Qué tenemos entre manos?",
            user=user_name,
        )
    else:
        clean_user = str(user_name or "usuario").strip() or "usuario"
        clean_assistant = str(assistant_name or "Atlas").strip() or "Atlas"
        phrase = f"¡Buenas, {clean_user}! {clean_assistant} al habla."


    print()
    print(phrase)