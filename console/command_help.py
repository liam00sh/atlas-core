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
class HelpEntry:
    name: str
    description: str
    category: str
    examples: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    detail: str = ""
    owner_only: bool = False


CATEGORY_ORDER = (
    "General", "Usuarios", "Telegram", "Memoria", "Organización",
    "Identidad y modos", "Internet y fuentes", "Redacción",
    "Sistema y administración",
)

# Operaciones que viven en mixins y servicios, no necesariamente como módulos
# commands/*.py. Se mantienen aquí para que la ayuda describa el Atlas real.
CONVERSATIONAL_ENTRIES = (
    HelpEntry(
        "crear perfil de usuario",
        "Crea un perfil Atlas para una persona que Atlas ya conoce. Solo Liam puede hacerlo.",
        "Usuarios",
        ("crear perfil de usuario para Mary", "crear perfil Atlas para Lidia"),
        ("alta", "persona conocida", "perfil", "usuario"),
        detail="La persona debe existir previamente en el registro de personas. No crea personas desconocidas.",
        owner_only=True,
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
        ("cambiar usuario a Saray",),
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
        "iniciar bot de Telegram",
        "Inicia el bot desde la cuenta que se desea vincular y genera un código temporal.",
        "Telegram",
        ("/start",),
        ("código", "temporal", "vincular", "cuenta"),
        detail="Antes de este paso, Liam debe haber creado el perfil Atlas de esa persona.",
    ),
    HelpEntry(
        "confirmar código de Telegram",
        "Vincula el Telegram que generó el código temporal con el perfil indicado.",
        "Telegram",
        ("Confirma el código de Telegram ABC234DEFG para Mary",),
        ("confirmar", "vincular", "enlazar", "cuenta"),
        detail="Debe confirmarlo Liam desde su Telegram vinculado o desde la consola del PC.",
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
            category=str(meta.get("category", "General")).strip().title(),
            examples=tuple(str(x) for x in meta.get("examples", ()) if str(x).strip()),
            keywords=tuple(str(x) for x in meta.get("keywords", ()) if str(x).strip()),
            aliases=tuple(str(x) for x in meta.get("aliases", ()) if str(x).strip()),
            detail=str(meta.get("detail", "")).strip(),
        ))
    return entries


def all_entries() -> list[HelpEntry]:
    combined = _registered_entries() + list(CONVERSATIONAL_ENTRIES)
    result: list[HelpEntry] = []
    seen: set[str] = set()
    for entry in combined:
        key = _norm(entry.name)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def _search_blob(entry: HelpEntry) -> str:
    return _norm(" ".join((entry.name, entry.description, entry.category, *entry.examples, *entry.keywords, *entry.aliases)))


def search_entries(query: str, limit: int = 8) -> list[HelpEntry]:
    needle = _norm(query)
    if not needle:
        return []
    words = set(needle.split())
    scored: list[tuple[float, HelpEntry]] = []
    for entry in all_entries():
        blob = _search_blob(entry)
        matched = sum(1 for word in words if word in blob)
        ratio = SequenceMatcher(None, needle, _norm(entry.name)).ratio()
        if matched or ratio >= 0.55:
            scored.append((matched * 2.0 + ratio, entry))
    scored.sort(key=lambda item: (-item[0], _norm(item[1].name)))
    return [entry for _, entry in scored[:limit]]


def suggest_entries(text: str, limit: int = 4) -> list[HelpEntry]:
    return search_entries(text, limit=limit)


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


def render_help(topic: str | None = None) -> str:
    topic = (topic or "").strip()
    entries = all_entries()
    if topic:
        normalized = _norm(topic)
        category = next((cat for cat in CATEGORY_ORDER if _norm(cat) == normalized), None)
        matches = [e for e in entries if category and _norm(e.category) == _norm(category)]
        if not matches:
            exact = next((e for e in entries if _norm(e.name) == normalized or normalized in {_norm(a) for a in e.aliases}), None)
            if exact:
                return _entry_detail(exact)
            matches = search_entries(topic)
        if not matches:
            return f"No he encontrado comandos relacionados con «{topic}». Prueba con «ayuda» o «buscar comandos <tema>»."
        if len(matches) == 1:
            return _entry_detail(matches[0])
        return "Comandos relacionados con «{}»:\n\n{}".format(topic, "\n".join(f"• {e.name}: {e.description}" for e in matches))

    grouped: dict[str, list[HelpEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.category, []).append(entry)
    lines = ["=" * 34, "AYUDA DE ATLAS — COMANDOS", "=" * 34]
    categories = list(CATEGORY_ORDER) + sorted(set(grouped) - set(CATEGORY_ORDER))
    for category in categories:
        items = grouped.get(category)
        if not items:
            continue
        lines.extend(("", category.upper(), ""))
        for entry in sorted(items, key=lambda e: _norm(e.name)):
            suffix = " [solo Liam]" if entry.owner_only else ""
            lines.append(f"• {entry.name}{suffix}: {entry.description}")
    lines.extend((
        "",
        "Para ver más detalle: «ayuda <categoría o comando>».",
        "Para buscar por intención: «buscar comandos <tema>».",
    ))
    return "\n".join(lines)


def _natural_intent(text: str) -> str | None:
    n = _norm(text)
    guidance_patterns = (
        ("telegram", ("vincular", "enlazar", "codigo", "cuenta", "madre", "padre")),
        ("crear usuario", ("crear", "nuevo usuario", "nuevo perfil", "dar de alta")),
        ("memoria", ("recuerdo", "recordar", "olvidar", "que sabes")),
        ("modo", ("cambiar personalidad", "modo", "daxter", "coco")),
        ("recordatorio", ("avisame", "recuerdame", "recordatorio")),
        ("Internet", ("buscar", "internet", "web", "navegador")),
    )
    for topic, tokens in guidance_patterns:
        if any(token in n for token in tokens) and any(prefix in n for prefix in ("como", "quiero", "necesito", "que comando", "puedo", "debo")):
            return topic
    return None


def handle_command_help_request(text: str) -> str | None:
    n = _norm(text)
    if n in {
        "ayuda", "help", "comandos", "lista de comandos", "listar comandos",
        "mostrar comandos", "ver comandos", "que comandos hay", "menu", "menú",
    }:
        return render_help()

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
            return render_help(n[len(prefix):])
    for prefix in ("buscar comandos ", "buscar comando ", "buscar "):
        if n.startswith(prefix):
            topic = n[len(prefix):].strip()
            matches = search_entries(topic)
            if not matches:
                return f"No he encontrado comandos relacionados con «{topic}»."
            return "He encontrado estos comandos:\n\n" + "\n".join(f"• {e.name}: {e.description}" for e in matches)
    topic = _natural_intent(text)
    if topic:
        matches = search_entries(topic, limit=3)
        if matches:
            lead = "Para hacerlo, estos son los comandos u órdenes más útiles:\n\n"
            body = "\n\n".join(_entry_detail(entry) for entry in matches)
            return lead + body + "\n\nNo he ejecutado nada; solo te he indicado cómo hacerlo."
    # Sugerencias solo para entradas cortas que parecen una orden incompleta.
    if 1 <= len(n.split()) <= 4 and any(word in n for word in ("crear", "telegram", "usuario", "memoria", "record", "modo", "ayud", "version", "salir")):
        matches = suggest_entries(n)
        if matches:
            return "No existe exactamente ese comando. Quizá buscas alguno de estos:\n\n" + "\n".join(f"• {e.name}" for e in matches)
    return None
