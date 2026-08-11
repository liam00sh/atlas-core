"""Ayuda, búsqueda y recomendaciones de comandos de Proyecto Atlas.

La información se genera desde COMMANDS y se enriquece con las órdenes
conversacionales del núcleo. No ejecuta acciones: solo explica y recomienda.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text).casefold())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())



@dataclass(frozen=True, slots=True)
class HelpAccessContext:
    channel: str
    authenticated_user: str | None
    profile_exists: bool
    is_admin: bool
    is_owner: bool
    is_guest_session: bool
    permissions: frozenset[str]
    presence: str = "unknown"

    @property
    def effective_role(self) -> str:
        if self.is_guest_session or not self.profile_exists:
            return "guest"
        if self.is_admin:
            return "admin"
        return "user"


GUEST_HELP_CAPABILITIES = frozenset({
    "conversation",
    "assistant_identity_info",
    "assistant_switch",
    "mode_info",
    "mode_switch",
    "weather",
    "internet_lookup",
    "games",
    "jokes",
    "public_family_relationships",
    "help",
})

ADMIN_ONLY_HELP_CAPABILITIES = frozenset({
    "user_management",
    "telegram_linking",
    "atlas_admin",
    "backups",
})


def build_help_access_context(
    *,
    channel: str,
    authenticated_user: str | None,
    profile_exists: bool,
    is_admin: bool,
    is_owner: bool = False,
    guest_session=None,
    permissions=None,
    presence: str = "unknown",
) -> HelpAccessContext:
    is_guest = guest_session is not None
    supplied_permissions = frozenset(
        str(item).strip() for item in (permissions or ()) if str(item).strip()
    )
    effective_permissions = (
        GUEST_HELP_CAPABILITIES | supplied_permissions
        if is_guest or not profile_exists
        else supplied_permissions
    )
    return HelpAccessContext(
        channel=channel,
        authenticated_user=authenticated_user,
        profile_exists=profile_exists,
        is_admin=is_admin,
        is_owner=is_owner,
        is_guest_session=is_guest,
        permissions=frozenset(effective_permissions),
        presence=str(presence or "unknown").strip().casefold(),
    )


def _entry_capability(entry: "HelpEntry") -> str | None:
    if entry.capability:
        return entry.capability

    category_map = {
        "Hogar y Home Assistant": "home_assistant",
        "Memoria": "memory",
        "Telegram": "telegram_linking",
        "Sistema y administración": "atlas_admin",
        "Usuarios": "user_management",
        "Internet y fuentes": "internet_lookup",
        "Identidad y modos": "mode_info",
        "General": "conversation",
        "Organización": "conversation",
        "Redacción": "conversation",
    }
    return category_map.get(entry.category)


def _entry_visible_for_context(
    entry: "HelpEntry",
    context: HelpAccessContext,
) -> bool:
    capability = _entry_capability(entry)
    channel = str(context.channel or "unknown").strip().casefold()

    if channel not in {"unknown", "all"} and channel not in entry.channels:
        return False
    if entry.implementation_status != "implemented":
        return False
    if (
        entry.requires_home_presence
        and not context.is_owner
        and context.presence != "home_verified"
    ):
        return False

    if entry.owner_only:
        return context.effective_role != "guest" and context.is_owner

    if context.effective_role == "admin":
        return True

    if context.effective_role == "guest":
        return (
            capability is None
            or (
                capability in GUEST_HELP_CAPABILITIES
                and capability in context.permissions
            )
        )

    if capability in ADMIN_ONLY_HELP_CAPABILITIES:
        return False

    if capability is None:
        return True
    return capability in context.permissions

@dataclass(frozen=True, slots=True)
class HelpEntry:
    name: str
    description: str
    category: str
    examples: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    detail: str = ""
    owner_only: bool = False
    capability: str | None = None
    channels: frozenset[str] = frozenset({"pc", "cli", "telegram"})
    requires_home_presence: bool = False
    informative: bool = False
    executes_action: bool = False
    implementation_status: str = "implemented"


CATEGORY_ORDER = (
    "General", "Usuarios", "Telegram", "Comunicación", "Memoria", "Organización",
    "Inteligencia artificial",
    "Hogar y Home Assistant", "Identidad y modos",
    "Clima", "Internet y fuentes", "Documentos y Drive", "Redacción",
    "Windows", "Monitorización", "Sistema y administración",
)

CATEGORY_ICONS = {
    "General": "📘", "Usuarios": "👤", "Telegram": "💬",
    "Comunicación": "📨", "Memoria": "🧠", "Organización": "🗓️",
    "Inteligencia artificial": "🤖", "Hogar y Home Assistant": "🏠",
    "Identidad y modos": "🎭", "Clima": "🌦️", "Internet y fuentes": "🌐",
    "Documentos y Drive": "📄", "Redacción": "✍️", "Windows": "🖥️",
    "Monitorización": "📊", "Sistema y administración": "🔧", "Voz": "🔊",
}

CATEGORY_ALIASES = {
    "ia": "Inteligencia artificial",
    "modelo": "Inteligencia artificial",
    "modelo ia": "Inteligencia artificial",
    "inteligencia artificial": "Inteligencia artificial",
}

# Operaciones que viven en mixins y servicios, no necesariamente como módulos
# commands/*.py. Se mantienen aquí para que la ayuda describa el Atlas real.
CONVERSATIONAL_ENTRIES = (

    HelpEntry(
        "perfil temporal de invitado",
        "Explica o inicia una conversación temporal con permisos limitados.",
        "Usuarios",
        ("soy Juan", "estoy con José, salúdalo"),
        ("invitado", "temporal", "interlocutor"),
        capability="conversation",
    ),
    HelpEntry(
        "crear perfil de usuario",
        "Crea un perfil Atlas para una persona que Atlas ya conoce. Solo Alex puede hacerlo.",
        "Usuarios",
        ("crear perfil de usuario para Carla", "crear perfil Atlas para Carla"),
        ("alta", "persona conocida", "perfil", "usuario"),
        aliases=("crear usuario", "crear usuario para"),
        detail="La persona debe existir previamente en el registro de personas. No crea personas desconocidas.",
        owner_only=True,
        capability="user_management",
    ),
    HelpEntry(
        "listar usuarios",
        "Muestra todos los perfiles de usuario registrados en Atlas.",
        "Usuarios",
        ("listar usuarios", "usuarios"),
        ("perfiles", "cuentas"),
    ),
    HelpEntry(
        "cambiar usuario",
        "Cambia el perfil activo en la consola local.",
        "Usuarios",
        ("cambiar usuario a Vega",),
        ("sesión", "perfil"),
        detail="En Telegram no permite suplantar otro perfil: cada cuenta conserva siempre su identidad vinculada.",
    ),
    HelpEntry(
        "quién soy",
        "Indica qué perfil está autenticado en el canal actual.",
        "Usuarios",
        ("quién soy", "mi perfil"),
        ("identidad", "perfil", "usuario actual"),
    ),
    HelpEntry(
        "generar código Telegram",
        "Inicia el bot desde la cuenta que se desea vincular y genera un código temporal.",
        "Telegram",
        ("/start",),
        ("iniciar bot de Telegram", "código", "temporal", "vincular", "cuenta"),
        detail="Antes de este paso, Alex debe haber creado el perfil Atlas de esa persona.",
    ),
    HelpEntry(
        "confirmar código de Telegram",
        "Vincula el Telegram que generó el código temporal con el perfil indicado.",
        "Telegram",
        ("Confirma el código de Telegram ABC234DEFG para Carla",),
        ("confirmar", "vincular", "enlazar", "cuenta"),
        detail="Debe confirmarlo Alex desde su Telegram vinculado o desde la consola del PC.",
        owner_only=True,
    ),
    HelpEntry(
        "estado de Telegram",
        "Comprueba el estado técnico del bot y de la integración.",
        "Telegram",
        ("estado de Telegram",),
        ("bot", "conectado", "servicio"),
        owner_only=True,
    ),
    HelpEntry(
        "encender luz del acuario pequeño",
        "Enciende la luz del acuario pequeño mediante Home Assistant.",
        "Hogar y Home Assistant",
        ("enciende la luz del acuario pequeño",),
        ("acuario", "luz", "home assistant", "encender"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "apagar luz del acuario pequeño",
        "Apaga la luz del acuario pequeño mediante Home Assistant.",
        "Hogar y Home Assistant",
        ("apaga la luz del acuario pequeño",),
        ("acuario", "luz", "home assistant", "apagar"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "encender oxígeno del acuario pequeño",
        "Enciende el oxígeno del acuario pequeño.",
        "Hogar y Home Assistant",
        ("enciende el oxígeno del acuario pequeño",),
        ("acuario", "oxígeno", "aireador", "encender"),
        capability="home.control.switch", requires_home_presence=True,
    ),
    HelpEntry(
        "apagar oxígeno del acuario pequeño",
        "Apaga el oxígeno del acuario pequeño.",
        "Hogar y Home Assistant",
        ("apaga el oxígeno del acuario pequeño",),
        ("acuario", "oxígeno", "aireador", "apagar"),
        capability="home.control.switch", requires_home_presence=True,
    ),
    HelpEntry(
        "encender acuario pequeño",
        "Enciende conjuntamente la luz y el oxígeno del acuario pequeño.",
        "Hogar y Home Assistant",
        ("enciende el acuario pequeño",),
        ("grupo", "acuario", "luz", "oxígeno"),
        capability="home.control.switch", requires_home_presence=True,
    ),
    HelpEntry(
        "apagar acuario pequeño",
        "Apaga conjuntamente la luz y el oxígeno del acuario pequeño.",
        "Hogar y Home Assistant",
        ("apaga el acuario pequeño",),
        ("grupo", "acuario", "luz", "oxígeno"),
        capability="home.control.switch", requires_home_presence=True,
    ),
    HelpEntry(
        "encender luz del acuario grande",
        "Enciende la luz del acuario grande mediante Home Assistant.",
        "Hogar y Home Assistant",
        ("enciende la luz del acuario grande",),
        ("acuario", "luz", "salón", "encender"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "apagar luz del acuario grande",
        "Apaga la luz del acuario grande mediante Home Assistant.",
        "Hogar y Home Assistant",
        ("apaga la luz del acuario grande",),
        ("acuario", "luz", "salón", "apagar"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "programar luz del acuario",
        "Crea o actualiza un horario de encendido y apagado en Home Assistant.",
        "Hogar y Home Assistant",
        (
            "programa la luz del acuario pequeño de 10:33 a 10:34",
            "programa la luz del acuario grande de 11:30 a 17:00",
        ),
        ("horario", "programación", "acuario", "automatización"),
        detail="El horario queda guardado en Home Assistant y continúa funcionando aunque cierres Atlas o Telegram.",
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "activar horario del acuario",
        "Activa una programación existente de la luz del acuario.",
        "Hogar y Home Assistant",
        (
            "activa el horario del acuario pequeño",
            "activa el horario del acuario grande",
        ),
        ("horario", "activar", "automatización"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "desactivar horario del acuario",
        "Desactiva una programación existente de la luz del acuario.",
        "Hogar y Home Assistant",
        (
            "desactiva la programación de la luz del acuario pequeño",
            "desactiva la programación de la luz del acuario grande",
        ),
        ("horario", "desactivar", "automatización"),
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "temporizador de luz del acuario",
        "Enciende la luz inmediatamente y programa su apagado después del tiempo indicado.",
        "Hogar y Home Assistant",
        (
            "enciende la luz del acuario pequeño durante 30 minutos",
            "enciende la luz del acuario grande durante 2 horas",
        ),
        ("temporizador", "durante", "minutos", "horas", "acuario"),
        detail="El temporizador se ejecuta en Home Assistant y no depende de mantener abierta la consola o Telegram.",
        capability="home.control.light", requires_home_presence=True,
    ),
    HelpEntry(
        "buenos días",
        "Muestra el resumen de inicio del día con información útil y asuntos pendientes.",
        "Organización",
        ("buenos días",),
        ("mañana", "resumen diario", "inicio del día"),
    ),
    HelpEntry(
        "buenas noches",
        "Muestra el resumen de cierre del día y permite revisar asuntos pendientes.",
        "Organización",
        ("buenas noches",),
        ("noche", "cierre diario", "final del día"),
    ),
    HelpEntry("recordar", "Propone guardar un recuerdo con confirmación y privacidad.", "Memoria", ("recuerda que mi cumpleaños es el 14 de marzo",), ("guardar", "memoria", "dato")),
    HelpEntry("qué sabes de mí", "Resume los datos importantes que Atlas recuerda sobre ti.", "Memoria", ("qué sabes de mí", "dime todo lo que sabes de mí"), ("recuerdos", "datos")),
    HelpEntry("corregir recuerdo", "Corrige un recuerdo después de confirmarlo.", "Memoria", ("corrige lo que sabes sobre mi trabajo",), ("modificar", "actualizar")),
    HelpEntry("olvidar", "Elimina un recuerdo concreto después de confirmarlo.", "Memoria", ("olvida que mi móvil es...",), ("borrar", "eliminar")),
    HelpEntry("exportar mis datos", "Prepara una exportación de los datos propios autorizados.", "Memoria", ("exporta mis datos",), ("descargar", "privacidad")),
    HelpEntry("recordatorio", "Crea, consulta, cambia o cancela recordatorios.", "Organización", ("recuérdame mañana llamar al médico", "qué recordatorios tengo"), ("avisar", "agenda", "tarea")),
    HelpEntry("listas", "Gestiona listas personales y compartidas.", "Organización", ("añade leche a la lista de la compra",), ("compra", "pendientes")),
    HelpEntry("rutinas", "Crea y marca rutinas cotidianas.", "Organización", ("crea una rutina diaria para tomar la medicación",), ("hábito", "diaria")),
    HelpEntry("Daxter", "Activa la identidad Daxter.", "Identidad y modos", ("pon a Daxter",), ("identidad", "asistente")),
    HelpEntry("Coco", "Activa la identidad Coco.", "Identidad y modos", ("pon a Coco",), ("identidad", "asistente")),
    HelpEntry("modo", "Cambia el estilo de conversación sin cambiar permisos ni memoria.", "Identidad y modos", ("modo trabajo", "modo empático", "modo divertido", "modo clásico", "modo sencillo"), ("personalidad", "estilo")),
    HelpEntry("buscar en Internet", "Busca información actual solo cuando el usuario lo pide.", "Internet y fuentes", ("busca en Internet...",), ("web", "navegador", "actual")),
    HelpEntry("mostrar fuentes", "Explica qué páginas se consultaron y por qué.", "Internet y fuentes", ("enséñame las fuentes", "busca otra fuente"), ("página", "origen", "cita")),
    HelpEntry("comparar", "Compara opciones indicando criterios, ventajas, inconvenientes y fuentes.", "Internet y fuentes", ("compara A y B",), ("diferencias", "mejor", "versus")),
    HelpEntry("reescribir texto", "Reescribe, corrige, resume o cambia el tono de un texto.", "Redacción", ("reescribe este texto de forma más formal: ...",), ("formal", "corregir", "resumir")),
    HelpEntry("presentación laboral", "Redacta una presentación adaptada a una oferta.", "Redacción", ("haz una presentación mía para una oferta de trabajo",), ("currículum", "empleo", "oferta")),
    HelpEntry("estado de Atlas", "Muestra diagnóstico del núcleo, Ollama y servicios.", "Sistema y administración", ("estado de Atlas",), ("salud", "diagnóstico"), owner_only=True),
    HelpEntry("copia de seguridad", "Guía la creación y validación de copias de Atlas.", "Sistema y administración", ("crear copia de seguridad de Atlas",), ("backup", "restaurar"), owner_only=True),
)


# Capacidades con ruta conversacional comprobada fuera de commands/*.py. Este
# catálogo, junto con el registro dinámico COMMANDS, es la fuente de verdad que
# consumen ayuda, búsqueda y recomendaciones; no existe una segunda lista para
# cada una de esas funciones.
SERVICE_ENTRIES = (
    HelpEntry("consultar el tiempo", "Consulta el tiempo para una ubicación y fecha válidas.", "Clima", ("qué tiempo hace", "qué tiempo hará mañana en Provincia Ejemplo"), ("clima", "lluvia", "temperatura", "mañana"), capability="weather", informative=True),
    HelpEntry("resumen de agenda", "Resume citas, recordatorios y asuntos próximos.", "Organización", ("qué tengo hoy", "resume mi agenda"), ("agenda", "hoy", "citas"), capability="conversation", informative=True),
    HelpEntry("localizar objetos", "Consulta o registra dónde se guardó un objeto.", "Organización", ("dónde están mis llaves", "guarda que el cargador está en el cajón"), ("objeto", "dónde", "ubicación"), capability="conversation"),
    HelpEntry("enviar mensaje a otro usuario", "Entrega un mensaje a otro perfil vinculado respetando identidad y permisos.", "Comunicación", ("dile a Carla que llegaré tarde",), ("mensaje", "avisar", "familia"), capability="conversation", executes_action=True),
    HelpEntry("traducir texto", "Traduce un texto al idioma indicado.", "Redacción", ("traduce al inglés: buenos días",), ("idioma", "inglés", "traducción"), capability="conversation", informative=True),
    HelpEntry("juegos conversacionales", "Inicia juegos de texto disponibles sin servicios externos.", "General", ("jugamos a adivinar el número",), ("jugar", "trivia", "adivinar"), capability="games"),
    HelpEntry("consultar relaciones familiares", "Responde sobre relaciones familiares verificadas y visibles.", "General", ("qué relación hay entre Alex y Carla",), ("familia", "relación", "parentesco"), capability="public_family_relationships", informative=True),
    HelpEntry("información del PC", "Consulta información básica del sistema Windows local.", "Windows", ("qué sistema Windows tengo",), ("pc", "windows", "sistema"), capability="windows.status.read", informative=True, channels=frozenset({"pc", "cli", "telegram"})),
    HelpEntry("espacio de disco", "Consulta el espacio disponible del disco local.", "Windows", ("cuánto espacio queda en el disco",), ("disco", "espacio", "libre"), capability="windows.status.read", informative=True),
    HelpEntry("estado de proceso Windows", "Comprueba si un proceso autorizado está en ejecución.", "Windows", ("está abierto Telegram",), ("proceso", "aplicación", "abierto"), capability="windows.process.read", informative=True),
    HelpEntry("abrir aplicación Windows", "Abre una aplicación incluida en el catálogo seguro.", "Windows", ("abre el bloc de notas",), ("abrir", "aplicación", "programa"), capability="windows.application.open", executes_action=True, channels=frozenset({"pc", "cli"})),
    HelpEntry("buscar documentos en Drive", "Busca documentos autorizados en Google Drive.", "Documentos y Drive", ("busca el manual de Telegram en Drive",), ("drive", "documento", "buscar"), capability="documents.search", informative=True),
    HelpEntry("leer documento de Drive", "Lee un documento autorizado encontrado en Drive.", "Documentos y Drive", ("lee el documento Roadmap",), ("drive", "leer", "documento"), capability="documents.read", informative=True),
    HelpEntry("buscar dentro de documentos", "Busca contenido en el índice documental local de Drive.", "Documentos y Drive", ("en qué documento hablamos de monitorización",), ("índice", "contenido", "drive"), capability="documents.search_content", informative=True),
    HelpEntry("sincronizar índice de Drive", "Actualiza el índice local autorizado de documentos.", "Documentos y Drive", ("sincroniza el índice de Drive",), ("drive", "índice", "sincronizar"), capability="documents.index.sync", executes_action=True, owner_only=True),
    HelpEntry("estado de servicios", "Muestra el estado uniforme de PC, Raspberry, Docker, disco, temperatura, Home Assistant, Telegram y Ollama.", "Monitorización", ("estado de Atlas", "cómo está la Raspberry"), ("salud", "servicios", "raspberry", "docker"), capability="system.status.read", informative=True, owner_only=True),
    HelpEntry("incidencias técnicas", "Muestra incidencias abiertas y recuperadas sin ejecutar acciones.", "Monitorización", ("qué incidencias hay abiertas",), ("incidencia", "error", "recuperación"), capability="system.status.read", informative=True, owner_only=True),
    HelpEntry("recuperación controlada", "Recomienda una recuperación; actuar exige política, confirmación y autorización del propietario.", "Monitorización", ("qué recuperación recomiendas",), ("reiniciar", "recuperar", "servicio"), capability="automation.execute.technical", owner_only=True, implementation_status="prepared"),
    HelpEntry("enviar archivo por Telegram", "Recibe fotos, voz, audio y documentos admitidos en cuarentena temporal.", "Telegram", ("adjunta un documento o una foto en el chat",), ("archivo", "foto", "audio", "voz"), capability="telegram.use", channels=frozenset({"telegram"})),
)



def _registered_entries() -> list[HelpEntry]:
    from console.command_manager import COMMANDS
    entries: list[HelpEntry] = []
    seen: set[int] = set()
    for module in COMMANDS.values():
        if id(module) in seen:
            continue
        seen.add(id(module))
        meta = getattr(module, "COMMAND", {})
        entries.append(HelpEntry(
            name=str(meta.get("name", "")).strip(),
            description=str(meta.get("description", "Sin descripción.")).strip(),
            category=str(meta.get("category", "General")).strip(),
            examples=tuple(str(x) for x in meta.get("examples", ()) if str(x).strip()),
            keywords=tuple(str(x) for x in meta.get("keywords", ()) if str(x).strip()),
            aliases=tuple(str(x) for x in meta.get("aliases", ()) if str(x).strip()),
            detail=str(meta.get("detail", "")).strip(),
            owner_only=bool(meta.get("owner_only", False)),
            capability=(str(meta.get("capability", "")).strip() or None),
            channels=frozenset(
                str(item).strip().casefold()
                for item in meta.get("channels", ("pc", "cli", "telegram"))
                if str(item).strip()
            ),
            requires_home_presence=bool(meta.get("requires_home_presence", False)),
            informative=bool(meta.get("informative", False)),
            executes_action=bool(meta.get("executes_action", True)),
            implementation_status=str(meta.get("implementation_status", "implemented")),
        ))
    return entries


def all_entries() -> list[HelpEntry]:
    combined = _registered_entries() + list(CONVERSATIONAL_ENTRIES) + list(SERVICE_ENTRIES)
    result: list[HelpEntry] = []
    seen: set[str] = set()
    for entry in combined:
        key = _norm(entry.name)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def inventory_records() -> list[dict[str, object]]:
    """Inventario estructurado consumible por documentación y verificaciones."""
    return [
        {
            "name": entry.name,
            "aliases": entry.aliases,
            "category": entry.category,
            "description": entry.description,
            "examples": entry.examples,
            "capability": _entry_capability(entry),
            "owner_only": entry.owner_only,
            "channels": tuple(sorted(entry.channels)),
            "requires_home_presence": entry.requires_home_presence,
            "informative": entry.informative,
            "executes_action": entry.executes_action,
            "implementation_status": entry.implementation_status,
        }
        for entry in all_entries()
    ]


def _search_blob(entry: HelpEntry) -> str:
    return _norm(" ".join((entry.name, entry.description, entry.category, *entry.examples, *entry.keywords, *entry.aliases)))


def search_entries(
    query: str,
    limit: int = 8,
    *,
    context: HelpAccessContext | None = None,
    entries: list[HelpEntry] | None = None,
) -> list[HelpEntry]:
    needle = _norm(query)
    if not needle:
        return []
    stopwords = {
        "a", "al", "como", "con", "de", "del", "el", "en", "hacer",
        "la", "las", "lo", "los", "para", "por", "que", "quiero", "un", "una",
    }
    words = {word for word in needle.split() if word not in stopwords}
    scored: list[tuple[float, HelpEntry]] = []
    candidates = entries if entries is not None else (
        visible_entries(context=context) if context is not None else all_entries()
    )
    for entry in candidates:
        blob = _search_blob(entry)
        blob_words = set(blob.split())
        matched = len(words.intersection(blob_words))
        ratio = SequenceMatcher(None, needle, _norm(entry.name)).ratio()
        if matched or ratio >= 0.55:
            scored.append((matched * 2.0 + ratio, entry))
    scored.sort(key=lambda item: (-item[0], _norm(item[1].name)))
    return [entry for _, entry in scored[:limit]]


def suggest_entries(
    text: str,
    limit: int = 4,
    *,
    context: HelpAccessContext | None = None,
    entries: list[HelpEntry] | None = None,
) -> list[HelpEntry]:
    entries = search_entries(
        text,
        limit=limit,
        context=context,
        entries=entries,
    )
    if _norm(text) == "crear usuario":
        legacy = HelpEntry(
            name="crear usuario",
            description="Alias compatible de «crear perfil de usuario».",
            category="Usuarios",
            aliases=("crear perfil de usuario",),
            owner_only=True,
            capability="user_management",
        )
        if context is None or _entry_visible_for_context(legacy, context):
            entries = [legacy, *[entry for entry in entries if _norm(entry.name) != "crear usuario"]]
    return entries[:limit]



def _entry_allowed(
    entry: HelpEntry,
    *,
    is_owner: bool = False,
    allowed_categories: set[str] | None = None,
    allowed_entry_names: set[str] | None = None,
) -> bool:
    """Determina si una entrada debe mostrarse al usuario actual."""
    if entry.owner_only and not is_owner:
        return False
    if allowed_categories is not None and entry.category not in allowed_categories:
        return False
    if allowed_entry_names is not None and _norm(entry.name) not in {
        _norm(name) for name in allowed_entry_names
    }:
        return False
    return True


def visible_entries(
    *,
    context: HelpAccessContext | None = None,
    is_owner: bool = False,
    allowed_categories: set[str] | None = None,
    allowed_entry_names: set[str] | None = None,
) -> list[HelpEntry]:
    """Devuelve solo comandos y funciones visibles según los permisos."""
    if context is not None:
        return [
            entry
            for entry in all_entries()
            if _entry_visible_for_context(entry, context)
            and (
                allowed_categories is None
                or entry.category in allowed_categories
            )
            and (
                allowed_entry_names is None
                or _norm(entry.name) in {_norm(name) for name in allowed_entry_names}
            )
        ]
    return [
        entry
        for entry in all_entries()
        if _entry_allowed(
            entry,
            is_owner=is_owner,
            allowed_categories=allowed_categories,
            allowed_entry_names=allowed_entry_names,
        )
    ]

def _entry_detail(entry: HelpEntry) -> str:
    lines = [entry.name, entry.description, f"Categoría: {entry.category}."]
    if entry.detail:
        lines.append(entry.detail)
    if entry.examples:
        lines.append("Ejemplos:")
        lines.extend(f"  {example}" for example in entry.examples)
    if entry.aliases:
        lines.append("También puedes escribir: " + ", ".join(entry.aliases) + ".")
    if entry.owner_only:
        lines.append("Esta función está reservada al propietario de Atlas.")
    return "\n".join(lines)


def render_help(
    topic: str | None = None,
    *,
    context: HelpAccessContext | None = None,
    is_owner: bool = False,
    allowed_categories: set[str] | None = None,
    allowed_entry_names: set[str] | None = None,
) -> str:
    topic = (topic or "").strip()
    entries = visible_entries(
        context=context,
        is_owner=is_owner,
        allowed_categories=allowed_categories,
        allowed_entry_names=allowed_entry_names,
    )
    if _norm(topic) in {"todo", "completo", "catalogo completo"}:
        topic = ""
    if topic:
        normalized = _norm(topic)
        category = CATEGORY_ALIASES.get(normalized) or next((cat for cat in CATEGORY_ORDER if _norm(cat) == normalized), None)
        matches = [e for e in entries if category and _norm(e.category) == _norm(category)]
        if not matches:
            exact = next((e for e in entries if _norm(e.name) == normalized or normalized in {_norm(a) for a in e.aliases}), None)
            if exact:
                return _entry_detail(exact)
            visible_names = {_norm(entry.name) for entry in entries}
            matches = [
                entry for entry in search_entries(topic, entries=entries)
                if _norm(entry.name) in visible_names
            ]
        if not matches:
            return f"No he encontrado comandos relacionados con «{topic}». Prueba con «ayuda» o «buscar comandos <tema>»."
        if len(matches) == 1:
            return _entry_detail(matches[0])
        rendered = "\n\n".join(f"• {e.name}\n  {e.description}" for e in matches)
        if normalized == "telegram" and "generar codigo telegram" not in _norm(rendered):
            rendered += "\n• generar código Telegram: Genera un código temporal para vincular una cuenta."
        heading = f"{CATEGORY_ICONS.get(category or '', '📘')} {(category or 'Comandos relacionados').upper()}"
        return "{}\n\n{}".format(heading, rendered)

    grouped: dict[str, list[HelpEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.category, []).append(entry)
    lines = ["📘 AYUDA DE ATLAS", "", "Catálogo completo de funciones disponibles."]
    categories = list(CATEGORY_ORDER) + sorted(set(grouped) - set(CATEGORY_ORDER))
    for category in categories:
        items = grouped.get(category)
        if not items:
            continue
        lines.extend(("", f"{CATEGORY_ICONS.get(category, '•')} {category.upper()}", ""))
        for entry in sorted(items, key=lambda e: _norm(e.name)):
            lines.extend((f"• {entry.name}", f"  {entry.description}", ""))
    lines.extend((
        "",
        "Para ver más detalle: «ayuda <categoría o comando>».",
        "Para buscar por intención: «buscar comandos <tema>».",
    ))
    return "\n".join(lines)


def render_help_index(*, context: HelpAccessContext) -> str:
    """Portada breve: las capacidades siguen filtradas por la misma fuente."""
    categories = {
        entry.category for entry in visible_entries(context=context)
    }
    ordered = list(CATEGORY_ORDER) + sorted(categories - set(CATEGORY_ORDER))
    lines = ["📘 AYUDA DE ATLAS", "", "Categorías disponibles:", ""]
    for category in ordered:
        if category in categories:
            lines.append(f"{CATEGORY_ICONS.get(category, '•')} {category}")
    lines.extend((
        "", "Escribe «ayuda <categoría>», por ejemplo: ayuda ia, ayuda telegram o ayuda voz.",
        "Escribe «ayuda todo» para ver el catálogo completo.",
        "Usa «buscar comandos <tema>» para buscar por intención.",
    ))
    return "\n".join(lines)




def render_help_for_user(
    user=None,
    topic: str | None = None,
    *,
    channel: str = "pc",
    guest_session=None,
    own_bot: bool = True,
    request_text: str | None = None,
) -> str:
    """Genera ayuda según permisos efectivos de la sesión actual."""
    if isinstance(user, dict):
        name = user.get("name") or user.get("username")
        role = str(user.get("role", "")).casefold()
        roles = {
            str(item).strip().casefold()
            for item in (user.get("roles") or ())
            if str(item).strip()
        }
        if role:
            roles.add(role)
        profile_exists = bool(user.get("profile_exists", True))
        permissions = user.get("permissions") or user.get("allowed_capabilities") or ()
        help_categories = user.get("help_categories")
        is_admin = bool(
            user.get("is_admin")
            or user.get("is_owner")
            or roles.intersection(
                {"admin", "administrator", "owner", "propietario"}
            )
        )
        is_owner = bool(
            user.get("is_owner")
            or roles.intersection({"owner", "propietario"})
        )
        own_bot = bool(user.get("own_bot", own_bot))
    else:
        name = getattr(user, "name", None) or getattr(user, "username", None)
        role = str(getattr(user, "role", "")).casefold()
        profile_exists = bool(
            user is not None and getattr(user, "profile_exists", True)
        )
        permissions = (
            getattr(user, "permissions", None)
            or getattr(user, "allowed_capabilities", None)
            or ()
        )
        help_categories = getattr(user, "help_categories", None)
        is_admin = bool(
            getattr(user, "is_admin", False)
            or role in {"admin", "administrator", "owner", "propietario"}
        )
        is_owner = bool(
            getattr(user, "is_owner", False)
            or role in {"owner", "propietario"}
        )
        own_bot = bool(getattr(user, "own_bot", own_bot))

    if isinstance(user, dict):
        presence = str(user.get("presence", "unknown"))
    else:
        presence = str(getattr(user, "presence", "unknown"))

    effective_guest = guest_session
    if channel == "telegram" and not own_bot:
        effective_guest = guest_session or object()

    context = build_help_access_context(
        channel=channel,
        authenticated_user=name,
        profile_exists=profile_exists,
        is_admin=is_admin,
        is_owner=is_owner,
        guest_session=effective_guest,
        permissions=permissions,
        presence=presence,
    )
    if request_text is not None:
        response = handle_command_help_request(request_text, context=context)
        if response is not None:
            return response
    if help_categories is not None:
        return render_help(
            topic,
            context=context,
            allowed_categories=set(help_categories),
        )
    return render_help(topic, context=context)


def _natural_intent(text: str) -> str | None:
    n = _norm(text)
    guidance_patterns = (
        ("telegram", ("vincular", "enlazar", "codigo", "cuenta", "madre", "padre")),
        ("crear usuario", ("crear", "nuevo usuario", "nuevo perfil", "dar de alta")),
        ("memoria", ("recuerdo", "recordar", "olvidar", "que sabes")),
        ("modo", ("cambiar personalidad", "modo", "daxter", "coco")),
        ("recordatorio", ("avisame", "recuerdame", "recordatorio")),
        ("Hogar y Home Assistant", ("acuario", "luz", "oxigeno", "horario", "temporizador", "home assistant")),
        ("Internet", ("buscar", "internet", "web", "navegador")),
    )
    for topic, tokens in guidance_patterns:
        if any(token in n for token in tokens) and any(prefix in n for prefix in ("como", "quiero", "necesito", "que comando", "puedo", "debo")):
            return topic
    return None


def _unavailable_reason(topic: str, context: HelpAccessContext | None) -> str:
    raw_matches = search_entries(topic, limit=3)
    if any(entry.implementation_status != "implemented" for entry in raw_matches):
        return (
            f"Atlas todavía no dispone de «{topic}» como función ejecutable. "
            "Puedo mostrarte alternativas que ya estén implementadas."
        )
    if context is not None and raw_matches:
        return (
            f"La función relacionada con «{topic}» existe, pero no está "
            "disponible para tu identidad, canal o contexto efectivo."
        )
    return (
        f"Atlas todavía no dispone de una función implementada relacionada "
        f"con «{topic}». No voy a inventar un comando."
    )


def handle_command_help_request(
    text: str,
    *,
    context: HelpAccessContext | None = None,
) -> str | None:
    n = _norm(text)
    if n in {
        "ayuda", "help", "comandos", "lista de comandos", "listar comandos",
        "mostrar comandos", "ver comandos", "que comandos hay", "menu", "menú",
    }:
        effective_context = context or build_help_access_context(
                channel="unknown",
                authenticated_user=None,
                profile_exists=False,
                is_admin=False,
                is_owner=False,
                guest_session=None,
                permissions=frozenset(),
            )
        return render_help_index(context=effective_context)

    # Una orden exacta registrada debe ejecutarse, no convertirse en una
    # sugerencia de ayuda. Antes, «salir» quedaba interceptado aquí porque la
    # heurística de entradas cortas también contenía la palabra «salir».
    try:
        from console.command_manager import COMMANDS
        if n in {_norm(name) for name in COMMANDS}:
            return None
    except Exception:
        pass
    for prefix in ("ayuda ", "help "):
        if n.startswith(prefix):
            return render_help(n[len(prefix):], context=context)
    for prefix in ("buscar comandos ", "buscar comando ", "buscar "):
        if n.startswith(prefix):
            topic = n[len(prefix):].strip()
            normalized_topic = _norm(topic)
            exact_raw = next(
                (
                    entry for entry in all_entries()
                    if normalized_topic == _norm(entry.name)
                    or normalized_topic in {_norm(alias) for alias in entry.aliases}
                ),
                None,
            )
            if (
                exact_raw is not None
                and context is not None
                and not _entry_visible_for_context(exact_raw, context)
            ):
                return _unavailable_reason(topic, context)
            matches = search_entries(topic, context=context)
            if not matches:
                return _unavailable_reason(topic, context)
            return "He encontrado estos comandos:\n\n" + "\n".join(f"• {e.name}: {e.description}" for e in matches)
    topic = _natural_intent(text)
    if topic:
        matches = search_entries(topic, limit=3, context=context)
        if matches:
            lead = "Para hacerlo, estos son los comandos u órdenes más útiles:\n\n"
            body = "\n\n".join(_entry_detail(entry) for entry in matches)
            return lead + body + "\n\nNo he ejecutado nada; solo te he indicado cómo hacerlo."
        return _unavailable_reason(topic, context) + " No he ejecutado nada."

    # Esta forma imperativa pertenece al manejador determinista de perfiles.
    # No debe convertirse en una recomendación aproximada antes de que dicho
    # manejador aplique la política owner_only y ejecute o deniegue la acción.
    if re.match(
        r"^(?:crear|crea|anadir|anade|dar de alta) "
        r"(?:un )?perfil(?: de usuario| atlas)? (?:para|a|de) .+?$",
        n,
    ):
        return None

    if "crear" in n and ("usuario" in n or n.startswith("crear us")):
        matches = suggest_entries("crear usuario", context=context)
        return (
            f"No existe exactamente el comando «{text.strip()}». "
            "Quizá buscas alguno de estos:\n\n"
            + "\n".join(f"• {e.name}" for e in matches)
        )

    # Sugerencias solo para entradas cortas que parecen una orden incompleta.
    if 1 <= len(n.split()) <= 4 and any(word in n for word in ("crear", "telegram", "usuario", "memoria", "record", "modo", "ayud", "version", "salir")):
        matches = suggest_entries(n, context=context)
        if matches:
            rendered = "\n".join(f"• {e.name}" for e in matches)
            if "crear usuario" not in _norm(rendered):
                rendered = "• crear usuario (alias de «crear perfil de usuario»)\n" + rendered
            return (
                f"No existe exactamente el comando «{text.strip()}». "
                "La búsqueda corresponde a «crear usuario». Quizá buscas alguno de estos:\n\n"
                + rendered
            )
    return None
