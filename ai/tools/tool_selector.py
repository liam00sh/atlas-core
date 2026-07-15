"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/tool_selector.py

Descripción:
    Determina si una entrada del usuario puede resolverse mediante
    una herramienta registrada en Atlas.

    El selector no ejecuta herramientas.

    Su única responsabilidad es decidir:

        - Si una herramienta resulta adecuada.
        - Qué herramienta debería utilizarse.
        - Con qué argumentos debería ejecutarse.
        - Por qué se ha seleccionado.

    La ejecución real corresponde a ToolRegistry.

Flujo:

    Mensaje del usuario
            │
            ▼
    ToolSelector.select()
            │
            ├── Coincidencia encontrada
            │       │
            │       ▼
            │   ToolSelection
            │
            └── Sin coincidencia
                    │
                    ▼
                   None

Importante:
    Esta primera versión utiliza reglas explícitas.

    El modelo de lenguaje todavía no puede elegir ni ejecutar
    herramientas directamente.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# dataclass permite representar una selección de herramienta
# mediante una estructura clara y tipada.
from dataclasses import dataclass
from dataclasses import field

# Any permite almacenar argumentos de distintos tipos.
from typing import Any

# Normaliza el texto recibido:
#
# - Convierte a minúsculas.
# - Elimina acentos.
# - Corrige determinadas erratas.
# - Reduce espacios.
from utils.text_normalizer import normalize_text

import re
import json


# =============================================================================
# RESULTADO DE LA SELECCIÓN
# =============================================================================

@dataclass
class ToolSelection:
    """
    Representa una herramienta seleccionada para una petición.

    Atributos:
        tool_name:
            Nombre interno de la herramienta.

            Ejemplo:
                get_current_datetime

        arguments:
            Argumentos que se enviarán a la herramienta.

        confidence:
            Nivel aproximado de confianza entre 0.0 y 1.0.

        reason:
            Explicación interna de por qué fue seleccionada.
    """

    tool_name: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float = 1.0

    reason: str = ""


# =============================================================================
# SELECTOR DE HERRAMIENTAS
# =============================================================================

class ToolSelector:
    """
    Selecciona una herramienta según el texto del usuario.

    El selector recibe el registro para comprobar que la herramienta
    elegida existe realmente antes de devolverla.
    """

    def __init__(
        self,
        registry,
    ) -> None:
        """
        Inicializa el selector.

        Parámetros:
            registry:
                Instancia de ToolRegistry que contiene
                las herramientas disponibles.
        """

        self.registry = registry

    def select(
        self,
        text: str,
    ) -> ToolSelection | None:
        """
        Busca una herramienta adecuada para la entrada recibida.

        Parámetros:
            text:
                Mensaje original del usuario.

        Devuelve:
            ToolSelection:
                Se ha encontrado una herramienta adecuada.

            None:
                Ninguna herramienta registrada puede responder
                de forma fiable a la petición.
        """

        normalized_text = normalize_text(
            text
        )

        if not normalized_text:
            return None

        # ---------------------------------------------------------------------
        # 1. FECHA Y HORA
        # ---------------------------------------------------------------------

        if self._matches_datetime(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_current_datetime",
                confidence=1.0,
                reason=(
                    "La entrada solicita información actual "
                    "sobre fecha, hora o día de la semana."
                ),
            )

        # ---------------------------------------------------------------------
        # 2. INFORMACIÓN DEL SISTEMA
        # ---------------------------------------------------------------------

        if self._matches_system_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_system_info",
                confidence=0.98,
                reason=(
                    "La entrada solicita información real "
                    "del sistema operativo o de Python."
                ),
            )

        # ---------------------------------------------------------------------
        # 3. INFORMACIÓN DE CPU
        # ---------------------------------------------------------------------

        if self._matches_cpu_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_cpu_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real "
                    "sobre el procesador del sistema."
                ),
            )

        # ---------------------------------------------------------------------
        # 4. MEMORIA RAM
        # ---------------------------------------------------------------------

        if self._matches_ram_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_ram_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real "
                    "sobre la memoria RAM del sistema."
                ),
            )

        # ---------------------------------------------------------------------
        # 5. INFORMACIÓN DE DISCOS
        # ---------------------------------------------------------------------

        if self._matches_disk_info(
            normalized_text
        ):

            requested_drive = self._extract_drive(
                normalized_text
            )

            arguments = {}

            if requested_drive is not None:
                arguments["drive"] = requested_drive

            return self._create_selection(
                tool_name="get_disk_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real sobre "
                    "las unidades de almacenamiento."
                ),
                arguments=arguments,
            )

        # ---------------------------------------------------------------------
        # 6. INFORMACIÓN DE GPU
        # ---------------------------------------------------------------------

        if self._matches_gpu_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_gpu_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real "
                    "sobre la tarjeta gráfica del sistema."
                ),
            )

        # ---------------------------------------------------------------------
        # 7. INFORMACIÓN LOCAL DE RED
        # ---------------------------------------------------------------------

        if self._matches_network_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_network_info",
                confidence=0.98,
                reason=(
                    "La entrada solicita información local "
                    "sobre interfaces o direcciones de red."
                ),
            )

        # ---------------------------------------------------------------------
        # 8. TIEMPO DE ACTIVIDAD
        # ---------------------------------------------------------------------

        if self._matches_uptime_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_uptime_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real "
                    "sobre el tiempo de actividad del sistema."
                ),
            )

        # ---------------------------------------------------------------------
        # 9. INFORMACIÓN DE BATERÍA
        # ---------------------------------------------------------------------

        if self._matches_battery_info(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_battery_info",
                confidence=0.99,
                reason=(
                    "La entrada solicita información real "
                    "sobre la batería del sistema."
                ),
            )

        # ---------------------------------------------------------------------
        # 10. MEMORIA
        # ---------------------------------------------------------------------

        if self._matches_memory_status(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_memory_status",
                confidence=0.97,
                reason=(
                    "La entrada solicita el número o estado "
                    "de los recuerdos del usuario activo."
                ),
            )

        # ---------------------------------------------------------------------
        # 11. USUARIO ACTIVO
        # ---------------------------------------------------------------------

        if self._matches_current_user(
            normalized_text
        ):

            return self._create_selection(
                tool_name="get_current_user",
                confidence=0.96,
                reason=(
                    "La entrada solicita información básica "
                    "sobre el usuario activo."
                ),
            )

        # ---------------------------------------------------------------------
        # PRUEBA DE CONFIRMACIÓN
        # ---------------------------------------------------------------------

        if self._matches_confirmation_test(
            normalized_text
        ):

            return self._create_selection(
                tool_name="test_confirmation",
                confidence=1.0,
                reason=(
                    "El usuario solicita probar el sistema "
                    "de confirmaciones."
                ),
            )

        # Ninguna herramienta puede responder de forma segura.
        return None
    
    def select_with_ai(
        self,
        text: str,
        provider,
    ) -> ToolSelection | None:
        """
        Solicita al modelo que proponga una herramienta.

        Este método solo se utiliza cuando el selector determinista
        no ha encontrado una coincidencia.

        El modelo no ejecuta la herramienta.

        Atlas valida después:

        - Que el nombre exista.
        - Que los argumentos sean un diccionario.
        - Que la confianza sea suficiente.
        - Que se respeten permisos y confirmaciones.
        """

        if provider is None:
            return None

        tool_metadata = self.registry.get_all_metadata()

        if not tool_metadata:
            return None

        prompt = self._build_ai_selection_prompt(
            text=text,
            tool_metadata=tool_metadata,
        )

        try:

            raw_response = provider.generate(
                prompt
            )

        except (
            RuntimeError,
            ValueError,
        ):

            return None

        return self._parse_ai_selection(
            raw_response
        )

    @staticmethod
    def _build_ai_selection_prompt(
        text: str,
        tool_metadata: list[dict],
    ) -> str:
        """
        Construye el prompt utilizado únicamente
        para seleccionar una herramienta.
        """

        serialized_tools = json.dumps(
            tool_metadata,
            ensure_ascii=False,
            indent=2,
        )

        return (
            "Actúas como selector interno de herramientas "
            "del Proyecto Atlas.\n\n"

            "Tu única tarea es decidir si alguna herramienta "
            "puede responder directamente a la petición.\n\n"

            "No respondas a la pregunta del usuario.\n"
            "No inventes herramientas.\n"
            "No escribas explicaciones fuera del JSON.\n"
            "Selecciona una herramienta solo cuando proporcione "
            "directamente los datos solicitados.\n\n"

            "Para preguntas generales, explicaciones, opiniones "
            "o conocimiento teórico, selecciona null.\n\n"

            "Ejemplos:\n"
            "- «Explícame qué es Docker» -> null\n"
            "- «¿Cuánta RAM libre tengo?» -> get_ram_info\n"
            "- «¿Qué temperatura tiene mi GPU?» -> get_gpu_info\n"
            "- «¿Qué ventajas tiene Linux?» -> null\n\n"

            "HERRAMIENTAS DISPONIBLES:\n"
            f"{serialized_tools}\n\n"

            "PETICIÓN DEL USUARIO:\n"
            f"{text}\n\n"

            "Devuelve exclusivamente un JSON válido con esta forma:\n\n"

            "{\n"
            '  "tool_name": "nombre_de_herramienta_o_null",\n'
            '  "arguments": {},\n'
            '  "confidence": 0.0,\n'
            '  "reason": "motivo breve"\n'
            "}\n\n"

            "Si no corresponde usar una herramienta, devuelve:\n\n"

            "{\n"
            '  "tool_name": null,\n'
            '  "arguments": {},\n'
            '  "confidence": 1.0,\n'
            '  "reason": "La petición requiere conversación general."\n'
            "}"
        )
    
    def _parse_ai_selection(
        self,
        raw_response: str,
    ) -> ToolSelection | None:
        """
        Convierte la respuesta del modelo en una selección segura.

        Cualquier respuesta inválida se descarta.
        """

        cleaned_response = raw_response.strip()

        # Eliminamos bloques Markdown si el modelo los añade.
        if cleaned_response.startswith("```"):

            cleaned_response = re.sub(
                r"^```(?:json)?\s*",
                "",
                cleaned_response,
                flags=re.IGNORECASE,
            )

            cleaned_response = re.sub(
                r"\s*```$",
                "",
                cleaned_response,
            )

        # Si el modelo añade texto alrededor, intentamos recuperar
        # únicamente el primer objeto JSON.
        start_index = cleaned_response.find(
        "{"
        )

        end_index = cleaned_response.rfind(
            "}"
        )

        if (
            start_index == -1
            or end_index == -1
            or end_index < start_index
        ):
            return None

        json_text = cleaned_response[
            start_index:
            end_index + 1
        ]

        try:

            data = json.loads(
                json_text
            )

        except json.JSONDecodeError:
            return None

        if not isinstance(
            data,
            dict,
        ):
            return None

        tool_name = data.get(
            "tool_name"
        )

        # null significa que no debe utilizarse ninguna herramienta.
        if tool_name is None:
            return None

        if not isinstance(
            tool_name,
            str,
        ):
            return None

        tool_name = tool_name.strip()

        if not self.registry.exists(
            tool_name
        ):
            return None

        arguments = data.get(
            "arguments",
            {},
        )

        if not isinstance(
            arguments,
            dict,
        ):
            return None

        raw_confidence = data.get(
            "confidence",
            0.0,
        )

        try:

            confidence = float(
                raw_confidence
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        confidence = max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )

        # Evitamos ejecutar propuestas demasiado dudosas.
        if confidence < 0.75:
            return None

        reason = data.get(
            "reason",
            "Selección propuesta por la IA.",
        )

        if not isinstance(
            reason,
            str,
        ):

            reason = (
                "Selección propuesta por la IA."
            )

        return ToolSelection(
            tool_name=tool_name,
            arguments=arguments,
            confidence=confidence,
            reason=reason.strip(),
        )

    def can_handle(
        self,
        text: str,
    ) -> bool:
        """
        Indica si existe una herramienta adecuada para la entrada.

        Este método no ejecuta la herramienta.
        """

        return self.select(
            text
        ) is not None

    def _create_selection(
        self,
        tool_name: str,
        confidence: float,
        reason: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolSelection | None:
        """
        Crea una selección únicamente si la herramienta existe.

        Esto evita devolver nombres de herramientas que no estén
        registradas realmente en ToolRegistry.
        """

        if not self.registry.exists(
            tool_name
        ):

            return None

        return ToolSelection(
            tool_name=tool_name,
            arguments=arguments or {},
            confidence=confidence,
            reason=reason,
        )

    @staticmethod
    def _contains_any(
        text: str,
        candidates: tuple[str, ...],
    ) -> bool:
        """
        Comprueba si el texto contiene alguna frase candidata.
        """

        return any(
            candidate in text
            for candidate in candidates
        )

    def _matches_datetime(
        self,
        text: str,
    ) -> bool:
        """
        Detecta preguntas relacionadas con fecha y hora.
        """

        exact_phrases = (
            "que hora es",
            "que hora es ahora",
            "dime la hora",
            "hora actual",
            "que fecha es hoy",
            "que dia es hoy",
            "en que dia estamos",
            "en que fecha estamos",
            "fecha actual",
            "dia actual",
            "que dia de la semana es",
            "que dia de la semana es hoy",
        )

        return self._contains_any(
            text,
            exact_phrases,
        )

    def _matches_system_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta preguntas sobre el sistema operativo y Python.

        No reconoce todavía CPU, RAM, GPU o almacenamiento,
        porque SystemInfoTool aún no devuelve esos datos.
        """

        system_phrases = (
            "que sistema operativo tengo",
            "que sistema operativo uso",
            "que sistema operativo estoy usando",
            "cual es mi sistema operativo",
            "version del sistema operativo",
            "informacion del sistema",
            "informacion de mi sistema",
            "version de python",
            "que version de python tengo",
            "que python tengo",
            "que version de python usa atlas",
            "que version de python estas usando",
        )

        return self._contains_any(
            text,
            system_phrases,
        )

    def _matches_memory_status(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas sobre la cantidad o el estado
        de los recuerdos persistentes del usuario activo.
        """

        memory_phrases = (
            "cuantos recuerdos tengo",
            "cuantas memorias tengo",
            "cuantos recuerdos hay",
            "cuantas memorias hay",
            "cuantos recuerdos hay guardados",
            "cuantas memorias hay guardadas",
            "numero de recuerdos",
            "numero de memorias",
            "cantidad de recuerdos",
            "cantidad de memorias",
            "estado de la memoria",
            "estado de mi memoria",
            "estado de los recuerdos",
            "estado de mis recuerdos",
            "cuantos datos recuerdas de mi",
            "cuantas cosas recuerdas de mi",

            # Variantes producidas actualmente por text_normalizer.
            "cuantos recuerdas tengo",
            "cuantos recuerdas hay",
            "cuantos recuerdas hay guardados",
            "numero de recuerdas",
            "cantidad de recuerdas",
            "estado de los recuerdas",
        )

        if self._contains_any(
            text,
            memory_phrases,
        ):
            return True

        contains_memory_term = self._contains_any(
            text,
            (
                "recuerdo",
                "recuerdos",
                "recuerda",
                "recuerdas",
                "memoria",
                "memorias",
            ),
        )

        contains_quantity_or_state = self._contains_any(
            text,
            (
                "cuanto",
                "cuantos",
                "cuanta",
                "cuantas",
                "numero",
                "cantidad",
                "estado",
                "guardado",
                "guardados",
                "guardada",
                "guardadas",
            ),
        )

        return (
            contains_memory_term
            and contains_quantity_or_state
        )

    def _matches_current_user(
        self,
        text: str,
    ) -> bool:
        """
        Detecta preguntas sobre el usuario activo.
        """

        user_phrases = (
            "quien soy",
            "que usuario soy",
            "cual es el usuario activo",
            "quien es el usuario activo",
            "usuario activo",
            "quien es el usuario principal",
            "cual es el usuario principal",
            "soy el usuario principal",
        )

        return self._contains_any(
            text,
            user_phrases,
        )
    
    def _matches_ram_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con la memoria RAM.
        """

        ram_phrases = (
            "cuanta ram tengo",
            "cuanta memoria ram tengo",
            "memoria ram instalada",
            "ram instalada",
            "cuanta ram hay instalada",
            "cuanta ram estoy usando",
            "cuanta ram estoy utilizando",
            "cuanta memoria ram estoy usando",
            "cuanta memoria ram estoy utilizando",
            "cuanta ram esta en uso",
            "uso de ram",
            "uso de memoria ram",
            "que porcentaje de ram uso",
            "porcentaje de ram",
            "cuanta ram queda libre",
            "cuanta memoria ram queda disponible",                "cuanta memoria ram tengo disponible",
            "cuanta ram tengo libre",
            "ram disponible",
            "memoria ram disponible",
            "estado de la ram",
            "informacion de la ram",
            "informacion de memoria ram",
        )

        return self._contains_any(
            text,
            ram_phrases,
        )
    
    def _matches_disk_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con discos
        y espacio de almacenamiento.
        """

        disk_phrases = (
            "que discos tengo",
            "que unidades tengo",
            "unidades de almacenamiento",
            "informacion de los discos",
            "informacion del disco",
            "estado de los discos",
            "estado del disco",
            "cuanto espacio tengo",
            "cuanto espacio libre tengo",
            "cuanto almacenamiento tengo",
            "cuanto almacenamiento queda",
            "cuanto espacio queda",
            "cuanto espacio disponible tengo",
            "espacio libre del disco",
            "espacio disponible del disco",
            "cuanto ocupa el disco",
            "cuanto espacio esta ocupado",
            "uso del disco",
            "porcentaje de uso del disco",
            "cuanto queda en c",
            "cuanto espacio queda en c",
            "espacio libre en c",
            "estado de c",
        )

        # También aceptamos consultas que contienen una unidad
        # de Windows junto a una palabra relacionada con almacenamiento.
        contains_drive = (
            self._extract_drive(text)
            is not None
        )

        contains_storage_term = self._contains_any(
            text,
            (
                "disco",
                "unidad",
                "espacio",
                "almacenamiento",
            ),
        )

        return (
            self._contains_any(
                text,
                disk_phrases,
            )
            or (
                contains_drive
                and contains_storage_term
            )
        )


    @staticmethod
    def _extract_drive(
        text: str,
    ) -> str | None:
        """
        Extrae una unidad de Windows de una consulta.

        Ejemplos:
            cuánto queda en C:
                -> C:

            espacio libre en d
                -> D:
        """

        match = re.search(
            r"\b([a-zA-Z])\s*:",
            text,
        )

        if match is None:

            match = re.search(
                r"\b(?:en|del|disco|unidad)\s+([a-zA-Z])\b",
                text,
            )

        if match is None:
            return None

        return (
            f"{match.group(1).upper()}:"
        )
    
    def _matches_gpu_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con la tarjeta gráfica.
        """

        gpu_phrases = (
            "que gpu tengo",
            "que grafica tengo",
            "que tarjeta grafica tengo",
            "cual es mi gpu",
            "cual es mi grafica",
            "cual es mi tarjeta grafica",
            "modelo de gpu",
            "modelo de la gpu",
            "modelo de la grafica",
            "modelo de tarjeta grafica",
            "informacion de la gpu",
            "informacion de la grafica",
            "informacion de la tarjeta grafica",
            "estado de la gpu",
            "estado de la grafica",
            "uso de gpu",
            "uso de la gpu",
            "porcentaje de uso de la gpu",
            "cuanta gpu estoy usando",
            "cuanta memoria tiene la gpu",
            "cuanta memoria tiene la grafica",
            "cuanta vram tengo",
            "cuanta vram estoy usando",
            "memoria de video disponible",
            "memoria de la gpu disponible",
            "temperatura de la gpu",
            "temperatura de gpu",
            "temperatura de la grafica",
            "temperatura tiene la gpu",
            "que temperatura tiene la gpu",
            "que temperatura tiene mi gpu",
            "que temperatura tiene la grafica",
            "a cuantos grados esta la gpu",
            "a cuantos grados esta la grafica",
            "que driver de nvidia tengo",
            "version del controlador de nvidia",
        )

        if self._contains_any(
            text,
            gpu_phrases,
        ):
            return True

        # Detección adicional por conceptos para aceptar
        # distintas formas naturales de formular la pregunta.
        contains_gpu_term = self._contains_any(
            text,
            (
                "gpu",
                "grafica",
                "tarjeta grafica",
                "vram",
                "nvidia",
            ),
        )

        contains_gpu_property = self._contains_any(
            text,
            (
                "temperatura",
                "grados",
                "uso",
                "porcentaje",
                "memoria",
                "modelo",
                "driver",
                "controlador",
                "estado",
                "informacion",
            ),
        )

        return (
            contains_gpu_term
            and contains_gpu_property
        )
    
    def _matches_network_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con la configuración
        local de red.

        No detecta todavía consultas sobre IP pública,
        velocidad real o disponibilidad de Internet.
        """

        network_phrases = (
            "cual es mi ip",
            "cual es mi ip local",
            "que ip tengo",
            "que ip local tengo",
            "direccion ip local",
            "mi direccion ip",
            "informacion de red",
            "informacion de mi red",
            "configuracion de red",
            "estado de la red",
            "que interfaces de red tengo",
            "que adaptadores de red tengo",
            "interfaces de red",
            "adaptadores de red",
            "que tarjeta de red tengo",
            "cual es mi direccion mac",
            "que direccion mac tengo",
            "direccion mac",
            "cual es el nombre de mi equipo",
            "como se llama mi ordenador",
            "nombre del equipo",
            "nombre del host",
            "hostname",
            "que mascara de red tengo",
            "cual es mi mascara de red",
            "mascara de red",
            "velocidad del adaptador de red",
            "velocidad de la tarjeta de red",
            "estado del wifi",
            "informacion del wifi",
            "estado de ethernet",
            "informacion de ethernet",
        )

        return self._contains_any(
            text,
            network_phrases,
        )
    
    def _matches_uptime_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con el tiempo
        de funcionamiento del sistema.
        """

        uptime_phrases = (
            "cuanto lleva encendido el ordenador",
            "cuanto lleva encendido el pc",
            "cuanto tiempo lleva encendido el ordenador",
            "cuanto tiempo lleva encendido el pc",
            "cuantos dias lleva encendido el ordenador",
            "cuantos dias lleva encendido el pc",
            "cuantas horas lleva encendido el ordenador",
            "cuantas horas lleva encendido el pc",
            "desde cuando esta encendido el ordenador",
            "desde cuando esta encendido el pc",
            "cuando se encendio el ordenador",
            "cuando se encendio el pc",
            "cuando se inicio windows",
            "cuando se inicio el sistema",
            "cuando arranco windows",
            "cuando arranco el sistema",
            "fecha de inicio del sistema",
            "hora de inicio del sistema",
            "tiempo de actividad",
            "tiempo de funcionamiento",
            "uptime",
            "uptime del sistema",
            "uptime del ordenador",
            "uptime del pc",
        )

        return self._contains_any(
            text,
            uptime_phrases,
        )
    
    def _matches_battery_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con la batería.
        """

        battery_phrases = (
            "cuanta bateria tengo",
            "cuanto porcentaje de bateria tengo",
            "porcentaje de bateria",
            "estado de la bateria",
            "informacion de la bateria",
            "queda bateria",
            "cuanta bateria queda",
            "cuanto dura la bateria",
            "cuanta autonomia queda",
            "autonomia de la bateria",
            "tiempo restante de bateria",
            "esta cargando",
            "esta conectado a la corriente",
            "tengo el cargador conectado",
            "bateria del portatil",
            "nivel de bateria",
        )

        return self._contains_any(
            text,
            battery_phrases,
        )
    
    def _matches_cpu_info(
        self,
        text: str,
    ) -> bool:
        """
        Detecta consultas relacionadas con el procesador.
        """

        cpu_phrases = (
            "que procesador tengo",
            "que cpu tengo",
            "cual es mi procesador",
            "cual es mi cpu",
            "modelo del procesador",
            "modelo de cpu",
            "informacion del procesador",
            "informacion de la cpu",
            "estado del procesador",
            "estado de la cpu",
            "cuantos nucleos tiene mi procesador",
            "cuantos nucleos tiene mi cpu",
            "cuantos nucleos tengo",
            "cuantos hilos tiene mi procesador",
            "cuantos hilos tiene mi cpu",
            "cuantos procesadores logicos tengo",
            "frecuencia del procesador",
            "frecuencia de la cpu",
            "velocidad del procesador",
            "uso del procesador",
            "uso de cpu",
            "porcentaje de cpu",
            "cuanta cpu estoy usando",
            "a cuanto esta trabajando la cpu",
        )

        return self._contains_any(
            text,
            cpu_phrases,
        )
    
    def _matches_confirmation_test(
        self,
        text: str,
    ) -> bool:
        """
        Detecta solicitudes para probar las confirmaciones.
        """

        phrases = (
            "probar confirmacion",
            "probar la confirmacion",
            "prueba de confirmacion",
            "probar confirmaciones",
            "probar sistema de confirmaciones",
            "ejecutar prueba de confirmacion",
        )

        return self._contains_any(
            text,
            phrases,
        )