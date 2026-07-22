"""Consulta web explícita, verificable y acotada para Proyecto Atlas."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
import re
import unicodedata
from typing import Iterable
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InternetSource:
    title: str
    url: str
    snippet: str
    source_type: str = "unknown"
    authority_score: float = 0.5
    published_at: str | None = None
    updated_at: str | None = None
    data_date: str | None = None
    consulted_at: str | None = None



SENSITIVE_PATTERNS = (
    r"\b(?:dni|nie|pasaporte|numero de seguridad social)\b",
    r"\b(?:diagnostico|medicacion|historial medico|salud mental)\b",
    r"\b(?:contrasena|password|token|clave privada|api key)\b",
    r"\b(?:direccion completa|cuenta bancaria|iban|tarjeta)\b",
)


def sanitize_external_query(query: str) -> str:
    """Bloquea o minimiza datos privados antes de cualquier consulta externa."""
    clean = " ".join(str(query).strip().split())
    plain = _plain(clean)
    if any(re.search(pattern, plain, re.IGNORECASE) for pattern in SENSITIVE_PATTERNS):
        raise InternetLookupError(
            "La consulta contiene datos privados o sensibles que no deben enviarse a Internet. "
            "Reformula la pregunta sin información personal."
        )
    clean = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[correo]", clean)
    clean = re.sub(r"\b(?:\+?34)?[6789]\d{8}\b", "[teléfono]", clean)
    return clean


def classify_source(source: InternetSource) -> InternetSource:
    host = urlparse(source.url).hostname or ""
    host = host.casefold().removeprefix("www.")
    official_suffixes = (".gob.es", ".gov", ".europa.eu", ".edu", ".ac.uk")
    if "wikidata.org" in host:
        kind, score = "primary_structured", 0.92
    elif "wikipedia.org" in host:
        kind, score = "encyclopedia", 0.78
    elif host.endswith(official_suffixes) or host in {"boe.es", "ine.es", "aemet.es"}:
        kind, score = "official", 1.0
    elif any(token in host for token in ("reuters", "apnews", "efe.com", "elpais", "elmundo", "lavanguardia")):
        kind, score = "news_media", 0.82
    elif any(token in host for token in ("reddit", "foro", "forum")):
        kind, score = "forum", 0.35
    elif any(token in host for token in ("amazon", "aliexpress", "ebay", "tienda", "shop")):
        kind, score = "commercial", 0.45
    else:
        kind, score = "web", 0.55
    return replace(
        source,
        source_type=kind,
        authority_score=score,
        consulted_at=source.consulted_at or datetime.now(UTC).isoformat(),
    )


class InternetSourceHistory:
    """Historial JSONL por usuario, separado de la memoria personal."""
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, *, user_id: str, query: str, sources: list[InternetSource], response: str | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "consulted_at": datetime.now(UTC).isoformat(),
            "user_id": str(user_id),
            "query": query,
            "sources": [asdict(source) for source in sources],
            "response": response,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def list_for_user(self, user_id: str, limit: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        rows: list[dict] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("user_id", "")).casefold() == str(user_id).casefold():
                rows.append(row)
        return rows[-max(1, limit):]

class InternetLookupError(RuntimeError):
    """Error controlado durante una consulta externa."""


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9ñ ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_entity_query(query: str) -> str:
    """Extrae la entidad principal sin confundir verbos con el nombre.

    Ejemplos:
      - ``cuántos habitantes tiene Beneixama`` -> ``Beneixama``
      - ``en qué comunidad está Caudete`` -> ``Caudete``
      - ``dónde está Villena`` -> ``Villena``
    """
    clean = " ".join(str(query).strip().split())
    patterns = (
        r"^(?:cu[aá]ntos?\s+habitantes\s+tiene|poblaci[oó]n(?:\s+actual)?\s+de)\s+(.+?)[?.!]*$",
        r"^(?:habitantes|poblaci[oó]n)\s+(?:de|en)\s+(.+?)[?.!]*$",
        r"^(?:cu[aá]l\s+es\s+la\s+poblaci[oó]n\s+de)\s+(.+?)[?.!]*$",
        r"^(?:en\s+qu[eé]\s+(?:comunidad(?:\s+aut[oó]noma)?|provincia|pa[ií]s|regi[oó]n)\s+(?:est[aá]|se\s+encuentra))\s+(.+?)[?.!]*$",
        r"^(?:a\s+qu[eé]\s+(?:comunidad(?:\s+aut[oó]noma)?|provincia|pa[ií]s|regi[oó]n)\s+pertenece)\s+(.+?)[?.!]*$",
        r"^(?:d[oó]nde\s+(?:est[aá]|se\s+encuentra))\s+(.+?)[?.!]*$",
        r"^(?:ubicaci[oó]n\s+de)\s+(.+?)[?.!]*$",
    )
    for pattern in patterns:
        match = re.match(pattern, clean, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .?!¡¿")
    return clean


def _is_population_query(query: str) -> bool:
    normalized = _plain(query)
    return "habitantes" in normalized or "poblacion" in normalized


def _is_location_query(query: str) -> bool:
    normalized = _plain(query)
    markers = (
        "en que comunidad", "comunidad autonoma", "en que provincia",
        "en que pais", "en que region", "donde esta", "donde se encuentra",
        "a que comunidad pertenece", "ubicacion de",
    )
    return any(marker in normalized for marker in markers)


def _get_json(url: str, timeout: float = 12.0) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": "ProyectoAtlas/0.2 (+local personal assistant)",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # nosec B310 - URLs HTTPS controladas
        payload = response.read().decode("utf-8", errors="replace")
    data = json.loads(payload)
    return data if isinstance(data, dict) else {}


def _wikidata_search(entity: str) -> list[dict]:
    params = urlencode({
        "action": "wbsearchentities",
        "search": entity,
        "language": "es",
        "uselang": "es",
        "type": "item",
        "limit": "8",
        "format": "json",
    })
    data = _get_json(f"https://www.wikidata.org/w/api.php?{params}")
    results = data.get("search", [])
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _select_wikidata_entity(entity: str, results: list[dict]) -> dict | None:
    exact = [item for item in results if _plain(item.get("label", "")) == _plain(entity)]
    candidates = exact or results
    if not candidates:
        return None
    # Favorece municipios/localidades españolas frente a coincidencias temáticas.
    def score(item: dict) -> tuple[int, int]:
        description = _plain(item.get("description", ""))
        place_score = sum(token in description for token in (
            "municipio de espana", "municipio espanol", "localidad de espana",
            "municipality of spain", "localidad", "municipio",
        ))
        return (place_score, -len(str(item.get("description", ""))))
    return sorted(candidates, key=score, reverse=True)[0]


def _wikidata_claims(item_id: str) -> dict:
    params = urlencode({
        "action": "wbgetentities", "ids": item_id, "props": "claims|labels|descriptions",
        "languages": "es", "format": "json",
    })
    return _get_json(f"https://www.wikidata.org/w/api.php?{params}")


def _wikidata_labels(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    params = urlencode({
        "action": "wbgetentities", "ids": "|".join(dict.fromkeys(ids)),
        "props": "labels", "languages": "es|en", "format": "json",
    })
    data = _get_json(f"https://www.wikidata.org/w/api.php?{params}")
    labels: dict[str, str] = {}
    for item_id, item in data.get("entities", {}).items():
        if not isinstance(item, dict):
            continue
        available = item.get("labels", {})
        label = ""
        if isinstance(available, dict):
            label = str((available.get("es") or available.get("en") or {}).get("value") or "")
        if label:
            labels[item_id] = label
    return labels


def _claim_entity_ids(claims: dict, prop: str) -> list[str]:
    values: list[str] = []
    for claim in claims.get(prop, []) if isinstance(claims, dict) else []:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and value.get("id"):
            values.append(str(value["id"]))
    return values


def _wikidata_population(query: str) -> list[InternetSource]:
    if not _is_population_query(query):
        return []
    query = sanitize_external_query(query)
    entity = _extract_entity_query(query)
    selected = _select_wikidata_entity(entity, _wikidata_search(entity))
    if not selected:
        return []
    item_id = str(selected.get("id") or "")
    label = str(selected.get("label") or entity)
    data = _wikidata_claims(item_id)
    claims = data.get("entities", {}).get(item_id, {}).get("claims", {}).get("P1082", [])
    candidates: list[tuple[str, int, str]] = []
    for claim in claims if isinstance(claims, list) else []:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        amount = str(value.get("amount") or "").lstrip("+") if isinstance(value, dict) else ""
        if not amount:
            continue
        year = ""
        points = claim.get("qualifiers", {}).get("P585", [])
        if points:
            time_value = points[0].get("datavalue", {}).get("value", {})
            match = re.match(r"[+-](\d{4})", str(time_value.get("time") or ""))
            if match:
                year = match.group(1)
        rank = 2 if claim.get("rank") == "preferred" else 1
        candidates.append((year, rank, amount))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    year, _rank, amount = candidates[0]
    try:
        formatted = f"{int(float(amount)):,}".replace(",", ".")
    except ValueError:
        formatted = amount
    date_note = f" según los datos de {year}" if year else ""
    snippet = f"{label} tiene {formatted} habitantes{date_note}."
    return [InternetSource(f"{label} — población", f"https://www.wikidata.org/wiki/{item_id}", snippet)]


def _wikidata_location(query: str) -> list[InternetSource]:
    if not _is_location_query(query):
        return []
    entity = _extract_entity_query(query)
    selected = _select_wikidata_entity(entity, _wikidata_search(entity))
    if not selected:
        return []
    item_id = str(selected.get("id") or "")
    label = str(selected.get("label") or entity)
    data = _wikidata_claims(item_id)
    claims = data.get("entities", {}).get(item_id, {}).get("claims", {})
    direct_ids = _claim_entity_ids(claims, "P131")
    country_ids = _claim_entity_ids(claims, "P17")
    hierarchy_ids: list[str] = list(direct_ids)
    frontier = list(direct_ids)
    for _ in range(4):
        next_frontier: list[str] = []
        for parent_id in frontier:
            parent_data = _wikidata_claims(parent_id)
            parent_claims = parent_data.get("entities", {}).get(parent_id, {}).get("claims", {})
            for ancestor in _claim_entity_ids(parent_claims, "P131"):
                if ancestor not in hierarchy_ids:
                    hierarchy_ids.append(ancestor)
                    next_frontier.append(ancestor)
        frontier = next_frontier
        if not frontier:
            break
    labels = _wikidata_labels(hierarchy_ids + country_ids)
    hierarchy = [labels[item] for item in hierarchy_ids if item in labels]
    country = [labels[item] for item in country_ids if item in labels]
    if not hierarchy and not country:
        return []
    pieces = []
    if hierarchy:
        pieces.append("se encuentra en " + ", ".join(hierarchy))
    if country:
        pieces.append("en " + ", ".join(country))
    snippet = f"{label} " + " ".join(pieces) + "."
    return [InternetSource(f"{label} — ubicación", f"https://www.wikidata.org/wiki/{item_id}", snippet)]


def _wikipedia_page(title: str) -> list[InternetSource]:
    params = urlencode({
        "action": "query", "prop": "extracts|info", "inprop": "url",
        "exintro": "1", "explaintext": "1", "redirects": "1",
        "titles": title, "format": "json", "utf8": "1",
    })
    data = _get_json(f"https://es.wikipedia.org/w/api.php?{params}")
    pages = data.get("query", {}).get("pages", {})
    sources: list[InternetSource] = []
    for page in pages.values() if isinstance(pages, dict) else []:
        if not isinstance(page, dict) or "missing" in page:
            continue
        snippet = str(page.get("extract") or "").strip()
        url = str(page.get("fullurl") or "").strip()
        title = str(page.get("title") or title).strip()
        if snippet and url:
            sources.append(InternetSource(title, url, snippet[:2200]))
    return sources


def _wikipedia_es(query: str) -> list[InternetSource]:
    entity = _extract_entity_query(query)
    exact = _wikipedia_page(entity)
    if exact:
        return exact[:1]
    params = urlencode({
        "action": "query", "list": "search", "srsearch": f'intitle:"{entity}"',
        "srlimit": "5", "format": "json", "utf8": "1",
    })
    data = _get_json(f"https://es.wikipedia.org/w/api.php?{params}")
    results = data.get("query", {}).get("search", [])
    titles = [str(item.get("title") or "") for item in results if isinstance(item, dict)]
    titles = [title for title in titles if title]
    titles.sort(key=lambda title: (0 if _plain(title) == _plain(entity) else 1, len(title)))
    sources: list[InternetSource] = []
    for title in titles[:3]:
        sources.extend(_wikipedia_page(title))
    return sources[:3]


def _duckduckgo(query: str) -> list[InternetSource]:
    params = urlencode({"q": query, "format": "json", "no_html": "1", "no_redirect": "1", "skip_disambig": "1"})
    data = _get_json(f"https://api.duckduckgo.com/?{params}")
    sources: list[InternetSource] = []
    abstract = str(data.get("AbstractText") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()
    heading = str(data.get("Heading") or query).strip()
    if abstract and abstract_url:
        sources.append(InternetSource(heading, abstract_url, abstract))
    def walk(items: Iterable[object]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            nested = item.get("Topics")
            if isinstance(nested, list):
                walk(nested)
                continue
            text = str(item.get("Text") or "").strip()
            url = str(item.get("FirstURL") or "").strip()
            if text and url and len(sources) < 4:
                sources.append(InternetSource(text.split(" - ", 1)[0], url, text))
    topics = data.get("RelatedTopics")
    if isinstance(topics, list):
        walk(topics)
    return sources



class _DuckDuckGoHTMLParser(HTMLParser):
    """Extractor mínimo de resultados públicos sin ejecutar JavaScript."""
    def __init__(self) -> None:
        super().__init__()
        self.results: list[InternetSource] = []
        self._in_title = False
        self._in_snippet = False
        self._href = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = str(values.get("class") or "")
        if tag == "a" and "result__a" in classes:
            self._in_title = True
            self._href = str(values.get("href") or "")
            self._title_parts = []
        elif tag in {"a", "div"} and "result__snippet" in classes:
            self._in_snippet = True
            self._snippet_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title:
            self._in_title = False
            title = unescape(" ".join(self._title_parts)).strip()
            if title and self._href:
                self.results.append(InternetSource(title, self._href, ""))
        if tag in {"a", "div"} and self._in_snippet:
            self._in_snippet = False
            snippet = unescape(" ".join(self._snippet_parts)).strip()
            if snippet and self.results and not self.results[-1].snippet:
                last = self.results[-1]
                self.results[-1] = InternetSource(last.title, last.url, snippet)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data.strip())
        if self._in_snippet:
            self._snippet_parts.append(data.strip())


def _duckduckgo_html(query: str) -> list[InternetSource]:
    """Búsqueda web general para consultas que no encajan en APIs temáticas."""
    params = urlencode({"q": query, "kl": "es-es"})
    request = Request(
        f"https://html.duckduckgo.com/html/?{params}",
        headers={
            "User-Agent": "Mozilla/5.0 ProyectoAtlas/0.3",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-ES,es;q=0.9",
        },
    )
    with urlopen(request, timeout=15.0) as response:  # nosec B310 - HTTPS controlado
        html = response.read().decode("utf-8", errors="replace")
    parser = _DuckDuckGoHTMLParser()
    parser.feed(html)
    return [item for item in parser.results if item.title and item.url][:8]


def is_comparison_query(query: str) -> bool:
    normalized = _plain(query)
    return any(marker in normalized for marker in (
        "compara ", "comparame", "comparativa", "diferencias entre",
        "cual es mejor", "que es mejor", "mejor opcion", "versus", " vs ",
    ))


def build_comparison_context(query: str, sources: list[InternetSource]) -> str:
    """Crea contexto trazable para que la IA compare sin inventar datos."""
    if not sources:
        return "No se encontraron fuentes suficientes para realizar una comparación fiable."
    lines = [f"Consulta comparativa: {query}", "Fuentes disponibles:"]
    for index, source in enumerate(sources[:6], start=1):
        snippet = " ".join(source.snippet.split())[:700]
        lines.append(f"{index}. {source.title}\n   URL: {source.url}\n   Extracto: {snippet or 'Sin extracto disponible.'}")
    lines.append(
        "Compara únicamente afirmaciones respaldadas por estas fuentes. "
        "Separa hechos, ventajas, inconvenientes y dudas pendientes. "
        "No declares un ganador sin indicar el criterio utilizado."
    )
    return "\n".join(lines)

def _source_is_relevant(source: InternetSource, entity: str) -> bool:
    entity_plain = _plain(entity)
    haystack = _plain(f"{source.title} {source.snippet}")
    tokens = [token for token in entity_plain.split() if len(token) > 2]
    return bool(tokens) and all(token in haystack for token in tokens)


def search_internet(
    query: str,
    *,
    user_id: str | None = None,
    history_path: str | Path | None = None,
    response_text: str | None = None,
) -> list[InternetSource]:
    """Busca una consulta explícita y devuelve fuentes relevantes y deduplicadas."""
    clean = sanitize_external_query(query)
    if not clean:
        raise ValueError("La consulta de Internet no puede estar vacía.")
    entity = _extract_entity_query(clean)
    providers = []
    if _is_population_query(clean):
        providers.append(_wikidata_population)
    if _is_location_query(clean):
        providers.append(_wikidata_location)
    providers.extend((_wikipedia_es, _duckduckgo, _duckduckgo_html))

    sources: list[InternetSource] = []
    errors: list[str] = []
    for provider in providers:
        try:
            sources.extend(provider(clean))
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(type(exc).__name__)

    unique: list[InternetSource] = []
    seen: set[str] = set()
    for source in sources:
        if source.url.casefold() in seen:
            continue
        # Evita que una consulta sobre Beneixama termine usando Caudete, Albacete
        # u otra localidad por contaminación del historial o una búsqueda ambigua.
        # Las consultas geográficas exigen coincidencia estricta para evitar
        # mezclar localidades. En búsquedas generales y comparativas se acepta
        # relevancia parcial, como haría un buscador convencional.
        if (_is_population_query(clean) or _is_location_query(clean)) and not _source_is_relevant(source, entity):
            continue
        seen.add(source.url.casefold())
        unique.append(source)
    if not unique and errors:
        raise InternetLookupError("No se pudo completar la consulta externa.")
    ranked = [classify_source(source) for source in unique]
    ranked.sort(key=lambda source: (-source.authority_score, source.title.casefold()))
    selected = ranked[:8]
    if user_id and history_path:
        InternetSourceHistory(history_path).record(
            user_id=user_id,
            query=clean,
            sources=selected,
            response=response_text,
        )
    return selected
