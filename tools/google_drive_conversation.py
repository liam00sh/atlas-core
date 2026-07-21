"""
===============================================================================
Proyecto Atlas
Archivo: tools/google_drive_conversation.py

Descripción:
    Controlador conversacional determinista para Google Drive.

    Convierte peticiones explícitas del usuario en operaciones del nuevo
    Tools Framework, sin permitir que el modelo ejecute herramientas
    directamente.

    Operaciones iniciales:
    - Buscar documentos por nombre.
    - Listar una carpeta.
    - Abrir un resultado por número.
    - Leer un documento por nombre.
    - Mantener un estado conversacional mínimo por usuario.
===============================================================================
"""

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Any, Protocol


ORDINALS = {
    "primero": 1,
    "primera": 1,
    "uno": 1,
    "segundo": 2,
    "segunda": 2,
    "dos": 2,
    "tercero": 3,
    "tercera": 3,
    "tres": 3,
    "cuarto": 4,
    "cuarta": 4,
    "cuatro": 4,
    "quinto": 5,
    "quinta": 5,
    "cinco": 5,
}


class FrameworkExecutor(Protocol):
    """Contrato mínimo que el controlador necesita de Atlas."""

    def execute_framework_tool(
        self,
        capability: str,
        *,
        arguments: dict | None = None,
        channel: str = "cli",
        metadata: dict | None = None,
    ) -> Any:
        ...

    def get_user(self) -> str:
        ...


@dataclass(slots=True)
class DriveConversationState:
    """Estado temporal y no persistente de una conversación con Drive."""

    search_results: list[dict[str, Any]] = field(
        default_factory=list
    )
    current_document: dict[str, Any] | None = None
    last_query: str | None = None
    session_id: str = "cli:default"
    path_candidates: list[dict[str, Any]] = field(default_factory=list)

    def clear_results(self) -> None:
        self.search_results.clear()
        self.last_query = None


@dataclass(frozen=True, slots=True)
class DriveConversationResponse:
    """Resultado del análisis conversacional."""

    handled: bool
    message: str = ""
    add_to_context: bool = True


class GoogleDriveConversationController:
    """
    Enrutador conversacional restringido a solicitudes explícitas de Drive.

    No usa IA para decidir si ejecutar una herramienta. El reconocimiento es
    deliberadamente conservador para evitar que una frase genérica como
    «busca información» active Google Drive por accidente.
    """

    MAX_RESULTS = 10
    PREVIEW_CHARS = 4000

    RAG_QUESTION_PATTERNS = (
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:responde|respondeme|respóndeme|contesta)"
            r"\s+(?:usando|con|basandote en|basándote en)"
            r"\s+(?:la\s+)?(?:documentacion|documentación|"
            r"documentos|indice|índice)"
            r"(?:\s+de\s+(?:google\s+)?drive|\s+de\s+atlas)?"
            r"[:;,]?\s+(?P<question>.+)$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:segun|según)"
            r"\s+(?:la\s+)?(?:documentacion|documentación|"
            r"documentos|indice|índice)"
            r"(?:\s+de\s+(?:google\s+)?drive|\s+de\s+atlas)?"
            r"[,;:]?\s+(?P<question>.+)$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:pregunta|consulta)"
            r"\s+(?:al|en el)\s+(?:indice|índice)"
            r"(?:\s+de\s+(?:google\s+)?drive)?"
            r"[:;,]?\s+(?P<question>.+)$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:que|qué)\s+dice"
            r"\s+(?:la\s+)?(?:documentacion|documentación)"
            r"(?:\s+de\s+atlas)?"
            r"\s+sobre\s+(?P<question>.+)$"
        ),
    )

    INDEX_SYNC_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?"
        r"(?:actualiza|actualizar|sincroniza|sincronizar|"
        r"crea|crear|reconstruye|reconstruir)"
        r"(?:\s+el)?\s+(?:indice|índice)\s+(?:de\s+)?(?:google\s+)?drive$"
    )

    INDEX_STATUS_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?"
        r"(?:estado|estado del (?:indice|índice)|como esta el (?:indice|índice)|"
        r"cómo está el índice|muestra el (?:indice|índice))"
        r"(?:\s+de\s+(?:google\s+)?drive)?$"
    )

    INDEX_CLEAR_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?"
        r"(?:borra|borrar|elimina|eliminar|limpia|limpiar)"
        r"(?:\s+el)?\s+(?:indice|índice)\s+(?:de\s+)?(?:google\s+)?drive$"
    )

    INDEX_SEARCH_PATTERNS = (
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar|encuentra|localiza)"
            r"(?:\s+en)?\s+el\s+(?:indice|índice)\s+(?:de\s+)?"
            r"(?:google\s+)?drive\s+(?P<query>.+)$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar)\s+(?P<query>.+?)"
            r"\s+en\s+el\s+(?:indice|índice)\s+(?:de\s+)?(?:google\s+)?drive$"
        ),
    )

    CONTENT_SEARCH_PATTERNS = (
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar|encuentra|localiza)"
            r"(?:\s+donde|\s+dónde)?"
            r"(?:\s+se)?\s+(?:habla|hablamos|dice|aparece)"
            r"(?:\s+de|\s+sobre)?\s+(?P<query>.+?)"
            r"(?:\s+en\s+(?:google\s+)?drive)?$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:donde|dónde|en que documento|en qué documento)"
            r"\s+(?:se\s+)?(?:habla|hablamos|dice|aparece)"
            r"(?:\s+de|\s+sobre)?\s+(?P<query>.+?)"
            r"(?:\s+en\s+(?:google\s+)?drive)?$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar)"
            r"\s+(?:dentro|en el contenido)"
            r"(?:\s+de)?\s+(?:google\s+)?drive"
            r"\s+(?P<query>.+)$"
        ),
    )

    SEARCH_PATTERNS = (
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar|encuentra|localiza)"
            r"(?:\s+en)?\s+(?:google\s+)?drive"
            r"(?:\s+(?:el|la|los|las|documento|archivo))?"
            r"\s*(?P<query>.+)$"
        ),
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:busca|buscar|encuentra|localiza)"
            r"\s+(?:el|la|los|las)?\s*"
            r"(?:documento|archivo)s?\s+"
            r"(?P<query>.+?)(?:\s+en\s+(?:google\s+)?drive)?$"
        ),
    )

    READ_PATTERNS = (
        re.compile(
            r"^(?:atlas[, ]+)?"
            r"(?:abre|abrir|lee|leer|muestra|mostrar)"
            r"(?:\s+el|\s+la)?"
            r"(?:\s+documento|\s+archivo)?"
            r"\s+(?P<target>.+)$"
        ),
    )

    LIST_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?"
        r"(?:lista|listar|muestra|mostrar|que hay|qué hay)"
        r"(?:\s+los)?(?:\s+archivos|\s+documentos|\s+contenido)?"
        r"(?:\s+de|\s+en)?\s+(?:google\s+)?drive"
        r"(?:\s+(?:raiz|raíz))?$"
    )

    NAVIGATE_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:ve a|entra en|abre la carpeta)\s+(?P<path>.+)$"
    )
    UP_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:sube|subir|vuelve)\s+(?:una\s+)?carpeta$"
    )
    ROOT_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:vuelve|ve|ir)\s+a\s+(?:la\s+raiz|la\s+raíz|atlas project)$"
    )
    PWD_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:donde estoy|dónde estoy|muestra la ruta|ruta actual)(?:\s+en\s+drive)?$"
    )
    TREE_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:muestra|muéstrame|ensena|enseña)(?:me)?\s+el\s+(?:arbol|árbol)(?:\s+de\s+drive)?(?:\s+desde\s+aqui|\s+desde\s+aquí)?$"
    )
    TREE_TARGET_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?(?:muestra|muéstrame|ensena|enseña)(?:me)?\s+el\s+(?:arbol|árbol)\s+de\s+(?P<path>.+)$"
    )
    SCOPED_SYNC_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?actualiza(?:\s+el)?\s+(?:indice|índice)\s+(?:de\s+)?(?P<target>.+?)(?P<recursive>\s+y\s+sus\s+subcarpetas)?$"
    )
    CURRENT_SYNC_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?actualiza(?:\s+(?:el\s+)?(?:indice|índice)\s+de)?\s+(?:solo\s+)?esta\s+carpeta(?:(?P<recursive>\s+y\s+(?:todas\s+)?sus\s+subcarpetas)|\s+sin\s+entrar\s+en\s+sus\s+subcarpetas)?$"
    )
    UPDATE_ONLY_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?actualiza\s+solo\s+(?P<target>.+)$"
    )
    GENERIC_SCOPED_UPDATE_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?actualiza\s+(?P<target>.+?)\s+y\s+(?:todas\s+)?sus\s+subcarpetas$"
    )
    LOCAL_INDEX_SEARCH_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?busca\s+(?P<query>.+?)\s+(?:solo\s+en\s+la\s+carpeta\s+actual|solo\s+desde\s+aqui|solo\s+desde\s+aquí)$"
    )
    GLOBAL_INDEX_SEARCH_PATTERN = re.compile(
        r"^(?:atlas[, ]+)?busca\s+(?P<query>.+?)\s+en\s+todo\s+(?:(?:google\s+)?drive|atlas\s+project)$"
    )

    @staticmethod
    def _intent_tokens(text: str) -> set[str]:
        normalized = unicodedata.normalize(
            "NFKD",
            text.casefold(),
        )
        without_accents = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        return set(
            re.findall(
                r"[a-z0-9_-]+",
                without_accents,
            )
        )

    @classmethod
    def _is_drive_list_intent(
        cls,
        text: str,
    ) -> bool:
        """
        Reconoce peticiones naturales de listado sin exigir una frase exacta.

        Ejemplos:
            mostrar el listado de Drive
            enséñame qué hay en Drive
            dime los archivos de Drive
            quiero ver el contenido de Drive
        """

        tokens = cls._intent_tokens(text)
        mentions_drive = (
            "drive" in tokens
            or {"atlas", "project"}.issubset(tokens)
        )
        if not mentions_drive:
            return False

        list_words = {
            "lista",
            "listado",
            "listar",
            "archivos",
            "documentos",
            "contenido",
            "carpetas",
        }
        display_words = {
            "mostrar",
            "muestra",
            "muestrame",
            "ensenar",
            "ensena",
            "ensename",
            "ver",
            "dime",
            "quiero",
            "hay",
        }

        return bool(
            tokens.intersection(list_words)
            and (
                tokens.intersection(display_words)
                or "listado" in tokens
                or "lista" in tokens
            )
        ) or (
            "hay" in tokens
            and mentions_drive
        )

    @classmethod
    def _is_index_status_intent(
        cls,
        text: str,
    ) -> bool:
        tokens = cls._intent_tokens(text)
        mentions_index = bool(
            tokens.intersection(
                {
                    "indice",
                    "indexado",
                    "indexacion",
                    "index",
                }
            )
        )
        status_words = {
            "estado",
            "situacion",
            "como",
            "actualizado",
            "actualizacion",
            "estadisticas",
            "datos",
            "informacion",
        }
        display_words = {
            "mostrar",
            "muestra",
            "muestrame",
            "dime",
            "ver",
            "ensenar",
            "ensena",
            "ensename",
        }
        return (
            mentions_index
            and bool(
                tokens.intersection(status_words)
                or tokens.intersection(display_words)
            )
            and not bool(
                tokens.intersection(
                    {
                        "actualiza",
                        "actualizar",
                        "sincroniza",
                        "sincronizar",
                        "borra",
                        "elimina",
                    }
                )
            )
        )

    @classmethod
    def _is_semantic_sync_intent(
        cls,
        text: str,
    ) -> bool:
        tokens = cls._intent_tokens(text)
        return (
            bool(
                tokens.intersection(
                    {
                        "semantico",
                        "semantica",
                        "embeddings",
                        "vectorial",
                    }
                )
            )
            and bool(
                tokens.intersection(
                    {
                        "actualiza",
                        "actualizar",
                        "crea",
                        "crear",
                        "sincroniza",
                        "sincronizar",
                        "reconstruye",
                    }
                )
            )
        )

    @classmethod
    def _is_semantic_status_intent(
        cls,
        text: str,
    ) -> bool:
        tokens = cls._intent_tokens(text)
        return (
            bool(
                tokens.intersection(
                    {
                        "semantico",
                        "semantica",
                        "embeddings",
                        "vectorial",
                    }
                )
            )
            and bool(
                tokens.intersection(
                    {
                        "estado",
                        "como",
                        "muestra",
                        "mostrar",
                        "dime",
                        "ver",
                    }
                )
            )
        )

    @classmethod
    def _semantic_query(
        cls,
        text: str,
    ) -> str | None:
        normalized = cls._normalize(text)
        patterns = (
            re.compile(
                r"^(?:atlas[, ]+)?"
                r"(?:busca|buscar|encuentra|localiza)"
                r"(?:\s+de\s+forma)?\s+"
                r"(?:semantica|semántica|semanticamente|semánticamente)"
                r"(?:\s+en\s+(?:google\s+)?drive)?"
                r"[:;,]?\s+(?P<query>.+)$"
            ),
            re.compile(
                r"^(?:atlas[, ]+)?"
                r"(?:busqueda|búsqueda)\s+(?:semantica|semántica)"
                r"(?:\s+en\s+(?:google\s+)?drive)?"
                r"[:;,]?\s+(?P<query>.+)$"
            ),
        )
        for pattern in patterns:
            match = pattern.fullmatch(normalized)
            if match:
                query = match.group("query").strip()
                return query or None
        return None

    def __init__(self) -> None:
        self._states: dict[
            tuple[str, str],
            DriveConversationState,
        ] = {}

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normaliza mayúsculas y espacios sin eliminar acentos.

        Los acentos forman parte del nombre real de los documentos de Drive.
        Eliminarlos antes de la consulta podía transformar, por ejemplo,
        «Constitución» en «constitucion» y provocar falsos negativos.
        """

        normalized = unicodedata.normalize(
            "NFC",
            text.casefold().strip(),
        )
        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )
        return normalized.strip(" .!?¿¡\"'")

    def _state_for(
        self,
        user: str,
        session_id: str = "cli:default",
    ) -> DriveConversationState:
        key = (self._normalize(user) or "default", session_id)
        return self._states.setdefault(
            key,
            DriveConversationState(session_id=session_id),
        )

    @classmethod
    def _extract_result_number(
        cls,
        normalized_text: str,
    ) -> int | None:
        direct_match = re.fullmatch(
            r"(?:el|la|numero|número|resultado)?\s*"
            r"(?P<number>\d+)",
            normalized_text,
        )
        if direct_match:
            return int(
                direct_match.group("number")
            )

        for word, number in ORDINALS.items():
            if re.fullmatch(
                rf"(?:el|la)?\s*{word}",
                normalized_text,
            ):
                return number

        match = re.search(
            r"(?:abre|lee|muestra|elige|selecciona)"
            r"(?:\s+el|\s+la|\s+resultado|\s+numero|\s+número)?"
            r"\s+(?P<value>\d+|"
            + "|".join(ORDINALS)
            + r")$",
            normalized_text,
        )
        if not match:
            return None

        value = match.group("value")
        if value.isdigit():
            return int(value)

        return ORDINALS.get(value)

    @staticmethod
    def _clean_query(query: str) -> str:
        cleaned = query.strip(" .!?¿¡\"'")
        cleaned = re.sub(
            r"\s+(?:en\s+)?(?:google\s+)?drive$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned.strip(" .!?¿¡\"'")

    @staticmethod
    def _tool_error_message(
        result: Any,
    ) -> str:
        error = getattr(result, "error", None)

        if error == "tool_disabled":
            return (
                "Google Drive está configurado en Atlas, pero la herramienta "
                "no está activa. Comprueba el token OAuth y reinicia Atlas."
            )

        if error == "permission_denied":
            return (
                "El usuario actual no tiene permiso para consultar "
                "Google Drive desde Atlas."
            )

        message = getattr(result, "message", "")
        return (
            message
            or "No he podido completar la consulta en Google Drive."
        )

    @staticmethod
    def _format_items(
        items: list[dict[str, Any]],
        *,
        heading: str,
    ) -> str:
        if not items:
            return (
                f"{heading}\n\n"
                "No he encontrado ningún elemento."
            )

        lines = [heading, ""]

        for index, item in enumerate(
            items,
            start=1,
        ):
            kind = (
                "Carpeta"
                if item.get("is_folder")
                else "Documento"
            )
            name = item.get("name") or "Sin nombre"
            lines.append(
                f"{index}. {name} — {kind}"
            )

        lines.extend(
            [
                "",
                (
                    "Puedes responder «abre el primero», "
                    "«lee el 2» o indicar el nombre."
                ),
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_content_matches(
        matches: list[dict[str, Any]],
        *,
        query: str,
    ) -> str:
        if not matches:
            return (
                "No he encontrado fragmentos relacionados con "
                f"«{query}» dentro de los documentos de Google Drive."
            )

        lines = [
            (
                f"He encontrado {len(matches)} documento(s) "
                f"relacionado(s) con «{query}»:"
            ),
            "",
        ]

        for index, match in enumerate(
            matches,
            start=1,
        ):
            item = match.get("item", {})
            name = item.get("name") or "Sin nombre"
            snippet = str(
                match.get("snippet", "")
            ).strip()
            web_url = item.get("web_url")

            lines.append(
                f"[{index}] {name}"
            )
            if snippet:
                lines.append(
                    f"    {snippet}"
                )
            if web_url:
                lines.append(
                    f"    Fuente: {web_url}"
                )
            lines.append("")

        lines.append(
            "Puedes pedirme que abra uno de los documentos o "
            "hacer una pregunta usando estos fragmentos."
        )
        return "\n".join(lines).strip()

    @staticmethod
    def _format_index_status(data: dict[str, Any]) -> str:
        if not data.get("exists"):
            return (
                "El índice documental de Google Drive todavía no existe. "
                "Puedes decir «actualiza el índice de Drive»."
            )

        return (
            "Estado del índice documental de Google Drive:\n\n"
            f"- Documentos: {data.get('document_count', 0)}\n"
            f"- Fragmentos: {data.get('chunk_count', 0)}\n"
            f"- Última actualización: {data.get('updated_at') or 'desconocida'}\n"
            f"- Ruta local: {data.get('path', '')}"
        )

    def _sync_semantic_index(
        self,
        atlas: FrameworkExecutor,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.semantic.sync",
            arguments={"batch_size": 16},
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_semantic_sync",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        data = result.data
        return DriveConversationResponse(
            True,
            (
                "Índice semántico actualizado.\n\n"
                f"- Fragmentos totales: {data.get('chunk_count', 0)}\n"
                f"- Nuevos o modificados: {data.get('embedded', 0)}\n"
                f"- Sin cambios: {data.get('unchanged', 0)}\n"
                f"- Eliminados: {data.get('removed', 0)}\n"
                f"- Modelo: {data.get('embedding_model') or 'desconocido'}"
            ),
        )

    def _semantic_status(
        self,
        atlas: FrameworkExecutor,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.semantic.status",
            arguments={},
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_semantic_status",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        data = result.data
        if not data.get("exists"):
            message = (
                "El índice semántico todavía no existe. "
                "Puedes decir «actualiza el índice semántico de Drive»."
            )
        else:
            message = (
                "Estado del índice semántico:\n\n"
                f"- Documentos: {data.get('document_count', 0)}\n"
                f"- Fragmentos: {data.get('chunk_count', 0)}\n"
                f"- Dimensión: {data.get('dimension') or 'desconocida'}\n"
                f"- Modelo: {data.get('embedding_model') or 'desconocido'}\n"
                f"- Actualizado: {data.get('updated_at') or 'desconocido'}"
            )

        return DriveConversationResponse(
            True,
            message,
        )

    def _search_semantic(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        query: str,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.semantic.search",
            arguments={
                "query": query,
                "limit": self.MAX_RESULTS,
                "max_per_document": 3,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_semantic_search",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        matches = list(
            result.data.get("matches", [])
        )
        state.search_results = [
            match.get("item", {})
            for match in matches
            if match.get("item")
        ]
        state.last_query = query
        state.current_document = None

        if not matches:
            return DriveConversationResponse(
                True,
                (
                    "No he encontrado resultados semánticos "
                    f"para «{query}»."
                ),
            )

        lines = [
            f"Resultados semánticos para «{query}»:",
            "",
        ]
        for position, match in enumerate(matches, 1):
            item = match.get("item", {})
            lines.append(
                f"{position}. {item.get('name', 'Documento')}"
            )
            lines.append(
                f"   Similitud: {float(match.get('score', 0.0)):.3f}"
            )
            text = str(match.get("text", "")).strip()
            if text:
                lines.append(
                    f"   {text[:500]}"
                )
            url = item.get("web_url")
            if url:
                lines.append(f"   {url}")
            lines.append("")

        return DriveConversationResponse(
            True,
            "\n".join(lines).strip(),
        )

    def _sync_index(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState | None = None,
        *,
        target_folder_id: str | None = None,
        target_file_id: str | None = None,
        recursive: bool = True,
    ) -> DriveConversationResponse:
        arguments: dict[str, Any] = {
            "max_items": 500,
            "folder_limit": 100,
        }
        if target_folder_id is not None or target_file_id is not None:
            arguments.update({
                "target_folder_id": target_folder_id,
                "target_file_id": target_file_id,
                "recursive": recursive,
            })
        result = atlas.execute_framework_tool(
            "documents.index.sync" if target_folder_id is None and target_file_id is None else "documents.index.sync_scope",
            arguments=arguments,
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_index_sync",
                "session_id": state.session_id if state else "cli:default",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        data = result.data
        message = (
            "Índice documental de Google Drive actualizado.\n\n"
            f"- Descubiertos: {data.get('discovered', 0)}\n"
            f"- Nuevos: {data.get('indexed', 0)}\n"
            f"- Actualizados: {data.get('updated', 0)}\n"
            f"- Sin cambios: {data.get('unchanged', 0)}\n"
            f"- Eliminados del índice: {data.get('removed', 0)}\n"
            f"- Omitidos: {data.get('skipped', 0)}\n"
            f"- Documentos indexados: {data.get('document_count', 0)}\n"
            f"- Fragmentos: {data.get('chunk_count', 0)}"
        )
        return DriveConversationResponse(True, message)

    def _index_status(
        self,
        atlas: FrameworkExecutor,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.index.status",
            arguments={},
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_index_status",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )
        return DriveConversationResponse(
            True,
            self._format_index_status(result.data),
        )

    def _clear_index(
        self,
        atlas: FrameworkExecutor,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.index.clear",
            arguments={},
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_index_clear",
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )
        return DriveConversationResponse(
            True,
            result.message,
        )

    @staticmethod
    def _format_rag_sources(
        sources: list[dict[str, Any]],
    ) -> str:
        lines = ["Fuentes utilizadas:"]

        for source in sources:
            number = source.get("number", "?")
            name = source.get(
                "name",
                "Documento sin nombre",
            )
            url = source.get("web_url")
            line = f"[{number}] {name}"
            if url:
                line += f"\n    {url}"
            lines.append(line)

        return "\n".join(lines)

    def _answer_with_rag(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        question: str,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.rag.answer",
            arguments={
                "question": question,
                "max_chunks": 8,
                "max_per_document": 3,
                "context_budget": 10000,
                "excerpt_chars": 900,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_rag_answer",
            },
        )

        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        sources = list(
            result.data.get("sources", [])
        )
        state.search_results = [
            {
                "item_id": source.get("item_id", ""),
                "name": source.get(
                    "name",
                    "Documento",
                ),
                "mime_type": "",
                "is_folder": False,
                "web_url": source.get("web_url"),
            }
            for source in sources
            if source.get("item_id")
        ]
        state.last_query = question
        state.current_document = None

        answer = str(
            result.data.get("answer", "")
        ).strip()
        source_text = self._format_rag_sources(
            sources
        )

        return DriveConversationResponse(
            True,
            f"{answer}\n\n{source_text}",
        )

    def _search_index(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        query: str,
        scope: dict[str, Any] | None = None,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.index.search",
            arguments={
                "query": query,
                "limit": self.MAX_RESULTS,
                "context_chars": 700,
                "scope": scope,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_index_search",
                "session_id": state.session_id,
            },
        )
        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        matches = list(
            result.data.get("matches", [])
        )
        state.search_results = [
            match.get("item", {})
            for match in matches
            if match.get("item")
        ]
        state.last_query = query
        state.current_document = None

        return DriveConversationResponse(
            True,
            self._format_content_matches(
                matches,
                query=query,
            ),
        )

    def _search_content(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        query: str,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.search_content",
            arguments={
                "query": query,
                "limit": self.MAX_RESULTS,
                "max_documents": 30,
                "context_chars": 700,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_content_search",
            },
        )

        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        matches = list(
            result.data.get("matches", [])
        )
        state.search_results = [
            match.get("item", {})
            for match in matches
            if match.get("item")
        ]
        state.last_query = query
        state.current_document = None

        return DriveConversationResponse(
            True,
            self._format_content_matches(
                matches,
                query=query,
            ),
        )

    def _search(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        query: str,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "documents.search",
            arguments={
                "query": query,
                "limit": self.MAX_RESULTS,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_search",
            },
        )

        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        items = list(
            result.data.get("items", [])
        )
        state.search_results = items
        state.last_query = query
        state.current_document = None

        if not items:
            return DriveConversationResponse(
                True,
                (
                    "No he encontrado documentos cuyo nombre contenga "
                    f"«{query}» en Google Drive."
                ),
            )

        return DriveConversationResponse(
            True,
            self._format_items(
                items,
                heading=(
                    f"He encontrado {len(items)} resultado(s) "
                    f"para «{query}»:"
                ),
            ),
        )

    def _list_root(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
    ) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "folders.list",
            arguments={
                "limit": self.MAX_RESULTS,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_list",
            },
        )

        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        items = list(
            result.data.get("items", [])
        )
        state.search_results = items
        state.last_query = None
        state.current_document = None

        return DriveConversationResponse(
            True,
            self._format_items(
                items,
                heading="Contenido disponible en Google Drive:",
            ),
        )

    def _read_item(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        item: dict[str, Any],
    ) -> DriveConversationResponse:
        if item.get("is_folder"):
            folder_id = item.get("item_id")
            result = atlas.execute_framework_tool(
                "folders.list",
                arguments={
                    "folder_id": folder_id,
                    "limit": self.MAX_RESULTS,
                },
                channel="cli",
                metadata={
                    "source": "conversation",
                    "intent": "drive_open_folder",
                },
            )

            if not result.success:
                return DriveConversationResponse(
                    True,
                    self._tool_error_message(result),
                )

            children = list(
                result.data.get("items", [])
            )
            state.search_results = children
            state.current_document = None

            return DriveConversationResponse(
                True,
                self._format_items(
                    children,
                    heading=(
                        f"Contenido de «{item.get('name', 'la carpeta')}»:"
                    ),
                ),
            )

        file_id = item.get("item_id")
        if not file_id:
            return DriveConversationResponse(
                True,
                "El resultado seleccionado no tiene un identificador válido.",
            )

        result = atlas.execute_framework_tool(
            "documents.read",
            arguments={
                "file_id": file_id,
                "max_chars": self.PREVIEW_CHARS,
            },
            channel="cli",
            metadata={
                "source": "conversation",
                "intent": "drive_read",
            },
        )

        if not result.success:
            return DriveConversationResponse(
                True,
                self._tool_error_message(result),
            )

        document_item = dict(
            result.data.get("item", item)
        )
        state.current_document = document_item

        content = str(
            result.data.get("content", "")
        ).strip()
        truncated = bool(
            result.data.get("truncated")
        )

        if not content:
            content = (
                "[El documento no contiene texto legible.]"
            )

        suffix = (
            "\n\n[Vista previa truncada.]"
            if truncated
            else ""
        )

        return DriveConversationResponse(
            True,
            (
                f"Documento: {document_item.get('name', 'Sin nombre')}\n\n"
                f"{content}{suffix}"
            ),
        )

    def _open_by_number(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        number: int,
    ) -> DriveConversationResponse:
        if not state.search_results:
            return DriveConversationResponse(
                False
            )

        if number < 1 or number > len(
            state.search_results
        ):
            return DriveConversationResponse(
                True,
                (
                    f"Solo hay {len(state.search_results)} resultado(s). "
                    "Indica uno de los números mostrados."
                ),
            )

        return self._read_item(
            atlas,
            state,
            state.search_results[number - 1],
        )

    def _read_by_name(
        self,
        atlas: FrameworkExecutor,
        state: DriveConversationState,
        target: str,
    ) -> DriveConversationResponse:
        normalized_target = self._normalize(target)

        for item in state.search_results:
            item_name = self._normalize(
                str(item.get("name", ""))
            )
            if (
                normalized_target == item_name
                or normalized_target in item_name
            ):
                return self._read_item(
                    atlas,
                    state,
                    item,
                )

        search_response = self._search(
            atlas,
            state,
            target,
        )

        if not search_response.handled:
            return search_response

        if len(state.search_results) == 1:
            return self._read_item(
                atlas,
                state,
                state.search_results[0],
            )

        return search_response

    @staticmethod
    def _navigation_metadata(state: DriveConversationState, intent: str) -> dict[str, Any]:
        return {"source": "conversation", "intent": intent, "session_id": state.session_id}

    def _pwd(self, atlas: FrameworkExecutor, state: DriveConversationState) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "drive.pwd", arguments={}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_pwd"),
        )
        if not result.success:
            return DriveConversationResponse(True, self._tool_error_message(result))
        entry = result.data.get("entry") or {}
        return DriveConversationResponse(True, f"Ruta actual de Drive: {entry.get('relative_path', 'Atlas Project')}")

    def _navigate(self, atlas: FrameworkExecutor, state: DriveConversationState, path: str) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "drive.cd", arguments={"path": path}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_cd"),
        )
        if not result.success:
            candidates = result.data.get("candidates", []) if isinstance(result.data, dict) else []
            if candidates:
                state.path_candidates = list(candidates)
                routes = "\n".join(f"{position}. {item.get('relative_path')}" for position, item in enumerate(candidates, 1))
                return DriveConversationResponse(True, f"La ruta es ambigua. Elige un número o indica una ruta completa:\n\n{routes}")
            return DriveConversationResponse(True, self._tool_error_message(result))
        entry = result.data.get("entry") or {}
        state.path_candidates.clear()
        return DriveConversationResponse(True, f"Ahora estás en: {entry.get('relative_path', path)}")

    def _navigate_candidate(self, atlas: FrameworkExecutor, state: DriveConversationState, number: int) -> DriveConversationResponse:
        if number < 1 or number > len(state.path_candidates):
            return DriveConversationResponse(True, f"Solo hay {len(state.path_candidates)} rutas candidatas.")
        candidate = state.path_candidates[number - 1]
        result = atlas.execute_framework_tool(
            "drive.cd", arguments={"folder_id": candidate.get("file_id")}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_cd_candidate"),
        )
        if not result.success:
            return DriveConversationResponse(True, self._tool_error_message(result))
        state.path_candidates.clear()
        entry = result.data.get("entry") or candidate
        return DriveConversationResponse(True, f"Ahora estás en: {entry.get('relative_path', entry.get('name', 'la carpeta seleccionada'))}")

    def _tree(self, atlas: FrameworkExecutor, state: DriveConversationState, depth: int = 2, folder_id: str | None = None) -> DriveConversationResponse:
        result = atlas.execute_framework_tool(
            "drive.tree", arguments={"depth": depth, "include_files": True, "folder_id": folder_id}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_tree"),
        )
        if not result.success:
            return DriveConversationResponse(True, self._tool_error_message(result))
        lines = ["Árbol de Drive desde la carpeta actual:", ""]
        for item in result.data.get("items", []):
            marker = "[D]" if item.get("is_folder") else "[F]"
            lines.append(f"{'  ' * max(0, int(item.get('depth', 1)) - 1)}{marker} {item.get('name', '')}")
        if len(lines) == 2:
            lines.append("[Carpeta vacía]")
        return DriveConversationResponse(True, "\n".join(lines))

    def _tree_target(self, atlas: FrameworkExecutor, state: DriveConversationState, path: str) -> DriveConversationResponse:
        resolved = atlas.execute_framework_tool(
            "drive.resolve_path", arguments={"path": path, "allow_file": False}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_tree_resolve"),
        )
        if not resolved.success:
            return DriveConversationResponse(True, self._tool_error_message(resolved))
        entry = resolved.data.get("entry") or {}
        return self._tree(atlas, state, folder_id=entry.get("file_id"))

    def _current_scope(self, atlas: FrameworkExecutor, state: DriveConversationState) -> dict[str, Any] | None:
        result = atlas.execute_framework_tool(
            "drive.pwd", arguments={}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_scope_current"),
        )
        if not result.success:
            return None
        entry = result.data.get("entry") or {}
        folder_id = entry.get("file_id")
        root_id = entry.get("root_id")
        if not folder_id:
            return None
        return {"type": "current", "target_id": folder_id, "root_folder_id": root_id}

    def _sync_target(self, atlas: FrameworkExecutor, state: DriveConversationState, target: str, recursive: bool) -> DriveConversationResponse:
        cleaned = target.strip()
        if cleaned.casefold() in {"esta carpeta", "aqui", "aquí", "."}:
            scope = self._current_scope(atlas, state)
            if scope is None:
                return DriveConversationResponse(True, "No he podido determinar la carpeta actual de Drive.")
            return self._sync_index(atlas, state, target_folder_id=scope["target_id"], recursive=recursive)
        result = atlas.execute_framework_tool(
            "drive.resolve_path", arguments={"path": cleaned, "allow_file": True}, channel="cli",
            metadata=self._navigation_metadata(state, "drive_resolve_index_scope"),
        )
        if not result.success:
            return DriveConversationResponse(True, self._tool_error_message(result))
        entry = result.data.get("entry") or {}
        if entry.get("is_folder"):
            return self._sync_index(atlas, state, target_folder_id=entry.get("file_id"), recursive=recursive)
        return self._sync_index(atlas, state, target_file_id=entry.get("file_id"), recursive=False)

    def handle(
        self,
        atlas: FrameworkExecutor,
        original_text: str,
        *,
        session_id: str = "cli:default",
    ) -> DriveConversationResponse:
        normalized = self._normalize(
            original_text
        )
        state = self._state_for(
            atlas.get_user(),
            session_id,
        )

        selected_number = (
            self._extract_result_number(
                normalized
            )
        )
        if selected_number is not None:
            if state.path_candidates:
                return self._navigate_candidate(atlas, state, selected_number)
            response = self._open_by_number(
                atlas,
                state,
                selected_number,
            )
            if response.handled:
                return response

        if self.PWD_PATTERN.fullmatch(normalized):
            return self._pwd(atlas, state)
        if self.UP_PATTERN.fullmatch(normalized):
            return self._navigate(atlas, state, "..")
        if self.ROOT_PATTERN.fullmatch(normalized):
            return self._navigate(atlas, state, "/")
        if self.TREE_PATTERN.fullmatch(normalized):
            return self._tree(atlas, state)
        tree_target = self.TREE_TARGET_PATTERN.fullmatch(normalized)
        if tree_target:
            return self._tree_target(atlas, state, tree_target.group("path"))
        navigation_match = self.NAVIGATE_PATTERN.fullmatch(normalized)
        if navigation_match:
            return self._navigate(atlas, state, navigation_match.group("path"))

        if (
            self.LIST_PATTERN.fullmatch(normalized)
            or self._is_drive_list_intent(normalized)
        ):
            return self._list_root(
                atlas,
                state,
            )

        if self._is_semantic_sync_intent(normalized):
            return self._sync_semantic_index(
                atlas
            )

        if self._is_semantic_status_intent(normalized):
            return self._semantic_status(
                atlas
            )

        semantic_query = self._semantic_query(
            normalized
        )
        if semantic_query:
            return self._search_semantic(
                atlas,
                state,
                semantic_query,
            )

        for pattern in self.RAG_QUESTION_PATTERNS:
            match = pattern.fullmatch(normalized)
            if match:
                question = self._clean_query(
                    match.group("question")
                )
                if not question:
                    return DriveConversationResponse(
                        True,
                        (
                            "Indícame qué pregunta quieres responder "
                            "con la documentación."
                        ),
                    )
                return self._answer_with_rag(
                    atlas,
                    state,
                    question,
                )

        if self.INDEX_SYNC_PATTERN.fullmatch(normalized):
            return self._sync_index(atlas, state)

        current_sync = self.CURRENT_SYNC_PATTERN.fullmatch(normalized)
        if current_sync:
            return self._sync_target(
                atlas, state, "esta carpeta", bool(current_sync.group("recursive"))
            )
        scoped_sync = self.SCOPED_SYNC_PATTERN.fullmatch(normalized)
        if scoped_sync:
            target = scoped_sync.group("target").strip()
            if target.casefold() not in {"drive", "google drive"}:
                return self._sync_target(
                    atlas, state, target, bool(scoped_sync.group("recursive"))
                )
        update_only = self.UPDATE_ONLY_PATTERN.fullmatch(normalized)
        if update_only:
            return self._sync_target(atlas, state, update_only.group("target"), False)
        generic_scoped = self.GENERIC_SCOPED_UPDATE_PATTERN.fullmatch(normalized)
        if generic_scoped:
            return self._sync_target(atlas, state, generic_scoped.group("target"), True)

        if (
            self.INDEX_STATUS_PATTERN.fullmatch(normalized)
            or self._is_index_status_intent(normalized)
        ):
            return self._index_status(atlas)

        if self.INDEX_CLEAR_PATTERN.fullmatch(normalized):
            return self._clear_index(atlas)

        local_search = self.LOCAL_INDEX_SEARCH_PATTERN.fullmatch(normalized)
        if local_search:
            scope = self._current_scope(atlas, state)
            if scope is None:
                return DriveConversationResponse(True, "No he podido determinar la carpeta actual de Drive.")
            return self._search_index(atlas, state, self._clean_query(local_search.group("query")), scope=scope)
        global_search = self.GLOBAL_INDEX_SEARCH_PATTERN.fullmatch(normalized)
        if global_search:
            return self._search_index(atlas, state, self._clean_query(global_search.group("query")), scope={"type": "global"})

        for pattern in self.INDEX_SEARCH_PATTERNS:
            match = pattern.fullmatch(normalized)
            if match:
                query = self._clean_query(
                    match.group("query")
                )
                if not query:
                    return DriveConversationResponse(
                        True,
                        "Indícame qué quieres buscar en el índice.",
                    )
                return self._search_index(
                    atlas,
                    state,
                    query,
                )

        for pattern in self.CONTENT_SEARCH_PATTERNS:
            match = pattern.fullmatch(
                normalized
            )
            if match:
                query = self._clean_query(
                    match.group("query")
                )
                if not query:
                    return DriveConversationResponse(
                        True,
                        (
                            "Indícame qué concepto quieres buscar "
                            "dentro de Google Drive."
                        ),
                    )
                return self._search_content(
                    atlas,
                    state,
                    query,
                )

        for pattern in self.SEARCH_PATTERNS:
            match = pattern.fullmatch(
                normalized
            )
            if match:
                query = self._clean_query(
                    match.group("query")
                )
                if not query:
                    return DriveConversationResponse(
                        True,
                        (
                            "Indícame qué documento quieres buscar "
                            "en Google Drive."
                        ),
                    )
                return self._search(
                    atlas,
                    state,
                    query,
                )

        for pattern in self.READ_PATTERNS:
            match = pattern.fullmatch(
                normalized
            )
            if not match:
                continue

            target = self._clean_query(
                match.group("target")
            )

            explicit_drive = (
                "drive" in normalized
                or "documento" in normalized
                or "archivo" in normalized
                or bool(state.search_results)
            )

            if not explicit_drive:
                return DriveConversationResponse(
                    False
                )

            if not target:
                return DriveConversationResponse(
                    True,
                    "Indícame qué documento quieres abrir.",
                )

            return self._read_by_name(
                atlas,
                state,
                target,
            )

        return DriveConversationResponse(
            False
        )
