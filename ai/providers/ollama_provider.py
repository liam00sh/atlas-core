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
import socket


from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


from ai.providers.base_provider import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """
    Proveedor de inteligencia artificial basado en Ollama.
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        timeout: int = 180,
    ) -> None:
        """
        Inicializa el proveedor.

        Parámetros:
            model_name:
                Nombre exacto del modelo instalado.

                Ejemplo:
                    qwen2.5:7b

            base_url:
                Dirección local de Ollama.

            timeout:
                Tiempo máximo de espera en segundos.
        """

        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request_json(
        self,
        path: str,
        method: str = "GET",
        payload: dict | None = None,
    ) -> dict:
        """
        Realiza una petición HTTP a Ollama.

        Este método es interno y centraliza toda la comunicación
        con la API local.
        """

        url = f"{self.base_url}{path}"

        request_data = None

        if payload is not None:
            request_data = json.dumps(
                payload
            ).encode(
                "utf-8"
            )

        request = Request(
            url=url,
            data=request_data,
            method=method,
            headers={
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                response_text = response.read().decode(
                    "utf-8"
                )

            return json.loads(
                response_text
            )

        except HTTPError as exception:
            try:
                detail = exception.read().decode(
                    "utf-8"
                )

            except OSError:
                detail = ""

            message = (
                f"Ollama devolvió el error HTTP "
                f"{exception.code}."
            )

            if detail:
                message += f" Detalle: {detail}"

            raise RuntimeError(
                message
            ) from exception

        except URLError as exception:
            raise RuntimeError(
                "No se ha podido conectar con Ollama. "
                "Comprueba que la aplicación esté iniciada."
            ) from exception

        except (
            TimeoutError,
            socket.timeout,
        ) as exception:
            raise RuntimeError(
                "Ollama ha tardado demasiado en responder."
            ) from exception

        except json.JSONDecodeError as exception:
            raise RuntimeError(
                "Ollama ha devuelto una respuesta JSON no válida."
            ) from exception

    def is_available(self) -> bool:
        """
        Comprueba si Ollama responde.
        """

        try:
            self._request_json(
                path="/api/tags",
            )

            return True

        except RuntimeError:
            return False

    def list_models(self) -> list[str]:
        """
        Devuelve los modelos instalados en Ollama.
        """

        response = self._request_json(
            path="/api/tags",
        )

        models = response.get(
            "models",
            [],
        )

        return [
            model["name"]
            for model in models
            if model.get("name")
        ]

    def is_model_installed(self) -> bool:
        """
        Comprueba si el modelo configurado está instalado.
        """

        return self.model_name in self.list_models()

    def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Envía el prompt al modelo configurado.

        Parámetros:
            prompt:
                Prompt completo construido por Atlas.

        Devuelve:
            str:
                Respuesta generada.

        Errores:
            ValueError:
                El prompt está vacío.

            RuntimeError:
                Ollama no está disponible, el modelo no existe
                o la respuesta está vacía.
        """

        prompt = prompt.strip()

        if not prompt:
            raise ValueError(
                "El prompt no puede estar vacío."
            )

        if not self.is_model_installed():
            raise RuntimeError(
                f"El modelo «{self.model_name}» "
                f"no está instalado en Ollama."
            )

        response = self._request_json(
            path="/api/generate",
            method="POST",
            payload={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,

                # Mantiene el modelo cargado durante cinco minutos.
                "keep_alive": "5m",

                "options": {
                    # Controla la creatividad.
                    # Un valor moderado aporta naturalidad
                    # sin hacer la respuesta demasiado impredecible.
                    "temperature": 0.7,
                },
            },
        )

        generated_text = response.get(
            "response",
            "",
        ).strip()

        if not generated_text:
            raise RuntimeError(
                "Ollama ha devuelto una respuesta vacía."
            )

        return generated_text

    def get_provider_name(self) -> str:
        """
        Devuelve el nombre del proveedor.
        """

        return "Ollama"

    def get_model_name(self) -> str:
        """
        Devuelve el nombre del modelo configurado.
        """

        return self.model_name