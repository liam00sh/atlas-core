"""
===============================================================================
Proyecto Atlas
Archivo: ai/providers/ollama_provider.py


Descripción:
    Implementa la comunicación entre Atlas y Ollama.


    Permite:


    - Comprobar si Ollama está disponible.
    - Consultar los modelos instalados.
    - Comprobar si el modelo configurado existe.
    - Enviar prompts.
    - Recuperar respuestas.
    - Gestionar errores de conexión.


===============================================================================
"""


import json
import re
import socket


from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


from ai.providers.base_provider import BaseAIProvider




class OllamaProvider(BaseAIProvider):
    """Proveedor de inteligencia artificial basado en Ollama."""


    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        timeout: int = 180,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout


    def _request_json(
        self,
        path: str,
        method: str = "GET",
        payload: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}{path}"
        request_data = None


        if payload is not None:
            request_data = json.dumps(payload).encode("utf-8")


        request = Request(
            url=url,
            data=request_data,
            method=method,
            headers={"Content-Type": "application/json"},
        )


        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_text = response.read().decode("utf-8")


            return json.loads(response_text)


        except HTTPError as exception:
            try:
                detail = exception.read().decode("utf-8")
            except OSError:
                detail = ""


            message = f"Ollama devolvió el error HTTP {exception.code}."


            if detail:
                message += f" Detalle: {detail}"


            raise RuntimeError(message) from exception


        except URLError as exception:
            raise RuntimeError(
                "No se ha podido conectar con Ollama. "
                "Comprueba que la aplicación esté iniciada."
            ) from exception


        except (TimeoutError, socket.timeout) as exception:
            raise RuntimeError(
                "Ollama ha tardado demasiado en responder."
            ) from exception


        except json.JSONDecodeError as exception:
            raise RuntimeError(
                "Ollama ha devuelto una respuesta JSON no válida."
            ) from exception


    def is_available(self) -> bool:
        try:
            self._request_json(path="/api/tags")
            return True
        except RuntimeError:
            return False


    def list_models(self) -> list[str]:
        response = self._request_json(path="/api/tags")
        models = response.get("models", [])
        return [model["name"] for model in models if model.get("name")]


    def is_model_installed(self) -> bool:
        return self.model_name in self.list_models()


    @staticmethod
    def _preferred_names_from_prompt(prompt: str) -> dict[str, str]:
        """Extrae nombre completo y nombre habitual del contexto del prompt."""

        entities = re.findall(
            r"(?:Persona|Animal) mencionad[oa]:\s*([^\n.]+)\.\s*\n"
            r"Nombre habitual preferido:\s*([^\n.]+)\.",
            str(prompt),
            flags=re.IGNORECASE,
        )
        return {full.strip(): preferred.strip() for full, preferred in entities}

    @staticmethod
    def _clean_generated_text(
        generated_text: str,
        prompt: str,
    ) -> str:
        """Elimina muletillas repetitivas y corrige concordancias frecuentes."""


        cleaned = str(generated_text).strip()


        if not cleaned:
            return cleaned

        # El modelo a veces copia un formato de transcripción completo.
        cleaned = re.sub(
            r"(?mi)^\s*(?:Coco|Daxter|Liam|Usuario|Asistente)\s*:\s*",
            "",
            cleaned,
        )

        # El modelo a veces se etiqueta a sí mismo aunque la consola ya lo hace.
        cleaned = re.sub(
            r"^\s*(?:Coco|Daxter)\s*:\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            # Solo retiramos un saludo completo. Exigir puntuación tras el
            # nombre evita mutilar frases válidas como «Hola Liam es...».
            r"^\s*[¡!]?hola(?:,\s*|\s+)"
            r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]*"
            r"\s*[,;:.!¡?¿\-–—]+\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\s*saludos,\s*(?:coco|daxter)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        # Si al retirar un saludo queda una coma o separador huérfano,
        # lo eliminamos antes de mostrar la respuesta.
        cleaned = re.sub(
            r"^[\s,;:.\-–—]+",
            "",
            cleaned,
        )


        generic_endings = (
            r"¿cómo estás hoy\?\s*estoy aquí para "
            r"(?:ayudarte|apoyarte)(?: si lo necesitas)?[.!]?",
            r"estoy aquí para (?:ayudarte|apoyarte)"
            r"(?: si lo necesitas)?[.!]?",
            r"¡?estamos (?:aquí para apoyarte|en esto juntos)!?",
            r"¿hay (?:algún|alguna) (?:detalle|aspecto|cosa) "
            r"(?:en particular )?(?:que te interese|sobre .+? "
            r"en lo que pueda ayudarte)(?: conocer)?\??",
        )


        previous = None
        while previous != cleaned:
            previous = cleaned
            for pattern in generic_endings:
                cleaned = re.sub(
                    rf"(?:\s*\n?\s*){pattern}\s*$",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                )


        grammar_replacements = {
            r"\beres muy felices juntos\b": "sois muy felices juntos",
            r"\bsoy tú,\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]*)\b": r"tú eres \1",
            r"\bme refieres a\b": "te refieres a",
            r"\bme refieres\b": "te refieres",
            r"\bcon ti\b": "contigo",
            r"\bperhaps\b": "quizá",
            r"\bestuda\b": "estudia",
            r"\bchico gato\b": "gato",
            r"\beres tan suerte teniéndola a su lado\b": "tienes mucha suerte de tenerla a tu lado",
            r"\btienes tan suerte teniéndola a su lado\b": "tienes mucha suerte de tenerla a tu lado",
            r"\beres afortunado de tenerla a su lado\b": "tienes suerte de tenerla a tu lado",
            r"\beres tan afortunado teniéndola a su lado\b": "tienes mucha suerte de tenerla a tu lado",
            r"\buna foto nuestra juntos\b": "una foto vuestra juntos",
            r"\buna foto nuestra juntas\b": "una foto vuestra juntas",
            r"\bLiam Navarro\b": "Liam",
            r"\bLiam Vicente Martínez\b": "Liam",
            r"\bSaray['’]s madre\b": "la madre de Saray",
            r"\becharse una mano\b": "echarte una mano",
            r"\bun amigo y una compañera\b": "una amiga y una compañera",
        }


        for pattern, replacement in grammar_replacements.items():
            cleaned = re.sub(
                pattern,
                replacement,
                cleaned,
                flags=re.IGNORECASE,
            )

        def fix_refers_to_proper_name(match: re.Match) -> str:
            return f"Te refieres a {match.group(1)}"

        cleaned = re.sub(
            r"\bte refieres al\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]*)",
            fix_refers_to_proper_name,
            cleaned,
            flags=re.IGNORECASE,
        )

        # Una tautología relacional indica que el modelo no resolvió el dato.
        # Es preferible reconocerlo a dejar una frase incompleta o engañosa.
        relation_articles = {
            "madre": "la",
            "padre": "el",
            "hermana": "la",
            "hermano": "el",
            "pareja": "la",
        }

        def replace_relation_tautology(match: re.Match) -> str:
            relation = match.group("relation").casefold()
            person = match.group("person")
            article = relation_articles.get(relation, "la")
            return (
                "No he identificado correctamente quién es "
                f"{article} {relation} de {person}"
            )

        cleaned = re.sub(
            r"\b(?:la|el)?\s*"
            r"(?P<relation>madre|padre|hermana|hermano|pareja)\s+de\s+"
            r"(?P<person>[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]+)\s+es\s+"
            r"(?:la|el)?\s*(?P=relation)\s+de\s+(?P=person)\b",
            replace_relation_tautology,
            cleaned,
            flags=re.IGNORECASE,
        )


        if (
            "Responde ahora como Coco" in prompt
            or "Coco habla de sí misma" in prompt
        ):
            feminine_replacements = {
                r"\bestaré encantado\b": "estaré encantada",
                r"\bestoy encantado\b": "estoy encantada",
                r"\bestoy preparado\b": "estoy preparada",
                r"\bestoy listo\b": "estoy lista",
                r"\bsoy organizado\b": "soy organizada",
                r"\bsoy resolutivo\b": "soy resolutiva",
            }


            for pattern, replacement in feminine_replacements.items():
                cleaned = re.sub(
                    pattern,
                    replacement,
                    cleaned,
                    flags=re.IGNORECASE,
                )


        # Evita volver a preguntar cómo está el usuario fuera de un saludo.
        user_message_match = re.search(
            r"MENSAJE DEL USUARIO\s*[:\n]+\s*(.+?)(?:\n\n|$)",
            str(prompt),
            flags=re.IGNORECASE | re.DOTALL,
        )
        user_message = (
            user_message_match.group(1).strip().casefold()
            if user_message_match
            else ""
        )
        is_greeting = bool(re.fullmatch(
            r"(?:hola|buenas|buenos dias|buenas tardes|buenas noches)[!. ]*",
            user_message,
        ))
        if not is_greeting:
            cleaned = re.sub(
                r"(?:\s*¿cómo estás(?: hoy)?\??|\s*¿qué tal estás\??)",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

        # Evita presentaciones sexualizadas u obscenas.
        cleaned = re.sub(
            r"\bsoy una zorrita muy juguetona y sociable\b",
            "soy una compañera muy despierta, sociable y bromista",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\bzorrita\b",
            "compañera",
            cleaned,
            flags=re.IGNORECASE,
        )

        # Usa el nombre habitual y evita artículos delante de nombres propios.
        for full_name, preferred_name in (
            OllamaProvider._preferred_names_from_prompt(prompt).items()
        ):
            cleaned = re.sub(
                rf"(?<!\w)(?:el|la)\s+{re.escape(full_name)}(?!\w)",
                preferred_name,
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                rf"(?<!\w){re.escape(full_name)}(?!\w)",
                preferred_name,
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                rf"(?<!\w)(?:el|la)\s+{re.escape(preferred_name)}(?!\w)",
                preferred_name,
                cleaned,
                flags=re.IGNORECASE,
            )

        # Elimina signos de apertura o cierre que hayan quedado aislados.
        cleaned = re.sub(r"(?m)^\s*[¡¿]+\s*$", "", cleaned)
        cleaned = re.sub(r"(?:\s|^)[¡¿]+\s*$", "", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(
            r"(?is)\s*(?:un saludo|saludos|atentamente),?\s*(?:coco|daxter)?\s*$",
            "",
            cleaned,
        )
        cleaned = re.sub(r"^[\s,;:.!¡?¿\-–—]+", "", cleaned).strip()
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned


    def generate(self, prompt: str) -> str:
        prompt = prompt.strip()


        if not prompt:
            raise ValueError("El prompt no puede estar vacío.")


        if not self.is_model_installed():
            raise RuntimeError(
                f"El modelo «{self.model_name}» no está instalado en Ollama."
            )


        response = self._request_json(
            path="/api/generate",
            method="POST",
            payload={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "5m",
                "options": {"temperature": 0.7},
            },
        )


        generated_text = response.get("response", "").strip()


        if not generated_text:
            raise RuntimeError("Ollama ha devuelto una respuesta vacía.")


        return self._clean_generated_text(generated_text, prompt)


    def get_provider_name(self) -> str:
        return "Ollama"


    def get_model_name(self) -> str:
        return self.model_name