"""Respuestas deterministas sobre Atlas, sus identidades y funciones.

Evita que Ollama improvise quién es Daxter/Coco, cómo funciona la memoria,
qué puede hacer Atlas o cómo se vincula una cuenta de Telegram.
"""
from __future__ import annotations

import re
import unicodedata


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip(" .!?¿¡")


class AtlasSelfKnowledgeMixin:
    """Conocimiento operativo y de identidad que no debe delegarse al LLM."""

    def _self_print(self, text: str) -> None:
        printer = getattr(self, "_print", None)
        if callable(printer):
            printer(text)
        else:
            print(text)

    def _active_assistant_name(self) -> str:
        manager = getattr(self, "identity_manager", None)
        for method_name in ("get_active_identity_name", "get_active_identity", "get_identity_name"):
            method = getattr(manager, method_name, None)
            if callable(method):
                try:
                    value = method()
                    if value:
                        return str(getattr(value, "name", value))
                except Exception:
                    pass
        return str(getattr(self, "name", "Daxter") or "Daxter")

    def _intro_for(self, person: str | None = None) -> str:
        name = self._active_assistant_name()
        greeting = f"Hola, {person.strip()} 😊\n\n" if person else ""
        identity = (
            f"Soy {name}, una de las identidades del asistente Atlas. "
            "Estoy aquí para ayudarte en el día a día y para trabajar con la memoria, "
            "las herramientas y los permisos que tengas disponibles."
        )
        examples = (
            "\n\nPuedo ayudarte, entre otras cosas, a:\n"
            "• resolver dudas y explicar cosas paso a paso;\n"
            "• crear recordatorios, listas y rutinas;\n"
            "• redactar, corregir, resumir o hacer más formal un texto;\n"
            "• preparar presentaciones personales, mensajes y documentos breves;\n"
            "• consultar y corregir recuerdos con tu permiso;\n"
            "• enviar mensajes entre familiares vinculados;\n"
            "• traducir y buscar en Internet cuando me lo pidas expresamente."
            "\n\nSi no entiendo bien lo que necesitas, te preguntaré antes de asumirlo."
        )
        return greeting + identity + examples

    def _identity_explanation(self, target: str) -> str:
        target = target.casefold()
        if target == "daxter":
            return (
                "Daxter es una identidad de Atlas con un estilo cercano, rápido, bromista y aventurero. "
                "Sigue siendo un asistente: la personalidad cambia la forma de hablar, no los permisos, "
                "la memoria ni las capacidades disponibles."
            )
        if target == "coco":
            return (
                "Coco es una identidad de Atlas con un estilo más tranquilo, amable, ordenado y cuidadoso. "
                "Sigue usando el mismo núcleo, memoria y herramientas autorizadas; cambia principalmente "
                "el tono y la manera de explicar las cosas."
            )
        return self._intro_for()

    def _comparison(self) -> str:
        return (
            "Daxter y Coco son dos identidades del mismo asistente Atlas.\n\n"
            "• Daxter: más bromista, directo, aventurero y enérgico.\n"
            "• Coco: más calmada, paciente, ordenada y suave al explicar.\n\n"
            "Cambiar de identidad no cambia tus recuerdos, tus permisos ni las funciones de Atlas. "
            "Solo cambia el estilo de conversación. Los modos, además, ajustan temporalmente el tono "
            "según la tarea, por ejemplo técnico, profesor, conductor o conversación informal."
        )

    def _memory_help(self) -> str:
        return (
            "La memoria de Atlas se guarda por usuario y con controles de privacidad.\n\n"
            "• Memoria conversacional: mantiene el hilo actual y después deja de ser relevante.\n"
            "• Memoria temporal: sirve para asuntos de horas o días, como una cita o una molestia, y caduca.\n"
            "• Memoria permanente: conserva datos útiles a largo plazo y normalmente requiere confirmación.\n\n"
            "Puedes preguntar «¿qué sabes de mí?», «¿por qué sabes eso?», «corrige este recuerdo», "
            "«archiva este dato» u «olvida este recuerdo». Las acciones sensibles se confirman antes de aplicarse."
        )

    def _telegram_help(self) -> str:
        return (
            "Para vincular a una persona con el bot de Telegram, esa persona debe abrir el bot desde su propia cuenta "
            "y completar el proceso de vinculación que muestra Atlas. La identidad se asocia al identificador real de "
            "Telegram, no solo al nombre que alguien escriba.\n\n"
            "Desde la cuenta de Liam puedes iniciar o administrar la vinculación con los comandos de administración "
            "habilitados en Atlas. Si me indicas qué pantalla o mensaje aparece, te guío paso a paso sin inventar datos."
        )

    def _capabilities_help(self) -> str:
        return self._intro_for().replace("Soy " + self._active_assistant_name() + ", una de las identidades del asistente Atlas. ", "Soy Atlas. ")

    def _handle_self_knowledge(self, text: str) -> bool:
        plain = _plain(text)

        # Presentarse a una persona presente no significa describirla.
        match = re.match(r"^(?:presentate|preséntate)\s+a\s+(.+)$", text.strip(), re.IGNORECASE)
        if match:
            self._self_print(self._intro_for(match.group(1).strip(" .!?")))
            return True

        if plain in {"presentate", "quien eres", "que eres", "hablame de ti", "dime quien eres"}:
            self._self_print(self._intro_for())
            return True

        if re.fullmatch(r"quien es daxter", plain):
            self._self_print(self._identity_explanation("daxter"))
            return True
        if re.fullmatch(r"quien es coco", plain):
            self._self_print(self._identity_explanation("coco"))
            return True
        if any(marker in plain for marker in ("diferencias entre daxter y coco", "diferencia entre daxter y coco", "compara daxter y coco")):
            self._self_print(self._comparison())
            return True

        if plain in {
            "que funciones tienes", "que cosas puedes hacer", "que puedes hacer",
            "cuales son tus funciones", "explica tus funciones", "como puedes ayudarme",
        }:
            self._self_print(self._capabilities_help())
            return True

        if any(marker in plain for marker in (
            "como funciona la memoria", "como almacenas datos", "como guardas los datos",
            "puedo modificar recuerdos", "puedo borrar recuerdos", "que tipos de memoria",
        )):
            self._self_print(self._memory_help())
            return True

        if any(marker in plain for marker in (
            "como vinculo su telegram", "como vincular telegram", "como añado una persona al bot",
            "como agregar una persona al bot", "como conecto su telegram con atlas",
        )):
            self._self_print(self._telegram_help())
            return True

        if any(marker in plain for marker in ("que modos tienes", "como funcionan los modos", "en que influyen los modos")):
            self._self_print(
                "Los modos adaptan temporalmente la forma de responder a la situación. Pueden hacer que Atlas sea más "
                "técnico, didáctico, breve, cuidadoso o informal. No cambian la identidad del usuario, los permisos ni "
                "la memoria. Daxter y Coco son identidades; los modos son ajustes de comportamiento dentro de ellas."
            )
            return True

        return False
