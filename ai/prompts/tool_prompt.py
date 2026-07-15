"""
===============================================================================
Proyecto Atlas
Archivo: ai/prompts/tool_prompt.py

Descripción:
    Construye el prompt utilizado para transformar el resultado técnico
    de una herramienta en una respuesta natural de Daxter.

    Las herramientas obtienen información real del sistema.

    El modelo de lenguaje no debe:

    - Modificar los valores obtenidos.
    - Inventar datos adicionales.
    - Contradecir el resultado de la herramienta.
    - Afirmar que ha consultado Internet cuando no lo ha hecho.
    - Ejecutar ninguna acción adicional.

    Su única función es explicar el resultado de forma clara,
    breve y natural.

Flujo:

    Herramienta
        │
        ▼
    ToolResult
        │
        ▼
    build_tool_response_prompt()
        │
        ▼
    Proveedor de IA
        │
        ▼
    Respuesta natural de Daxter

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import json

from typing import Any


# =============================================================================
# CONSTRUCCIÓN DEL PROMPT
# =============================================================================

def build_tool_response_prompt(
    user_message: str,
    tool_name: str,
    tool_message: str,
    tool_data: dict[str, Any] | None,
    user_name: str,
    assistant_name: str,
) -> str:
    """
    Construye un prompt para redactar de forma natural
    el resultado de una herramienta.

    Parámetros:
        user_message:
            Pregunta original realizada por el usuario.

        tool_name:
            Nombre interno de la herramienta ejecutada.

        tool_message:
            Resultado textual generado por la herramienta.

        tool_data:
            Datos estructurados devueltos por la herramienta.

        user_name:
            Nombre del usuario activo.

        assistant_name:
            Nombre del asistente.

    Devuelve:
        str:
            Prompt completo preparado para el proveedor de IA.
    """

    user_message = user_message.strip()
    tool_name = tool_name.strip()
    tool_message = tool_message.strip()
    user_name = user_name.strip()
    assistant_name = assistant_name.strip()

    if not user_message:

        raise ValueError(
            "El mensaje original del usuario no puede estar vacío."
        )

    if not tool_name:

        raise ValueError(
            "El nombre de la herramienta no puede estar vacío."
        )

    if not tool_message:

        raise ValueError(
            "El resultado de la herramienta no puede estar vacío."
        )

    # Los datos estructurados se incluyen como referencia adicional.
    #
    # Si no existen, se utiliza un objeto vacío.
    serialized_data = json.dumps(
        tool_data or {},
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return (
        f"Eres {assistant_name}, el asistente personal del "
        "Proyecto Atlas.\n\n"

        "Has recibido información REAL obtenida mediante una "
        "herramienta local controlada por Atlas.\n\n"

        "Tu única tarea es redactar una respuesta clara, natural "
        "y útil para el usuario.\n\n"

        "REGLAS OBLIGATORIAS\n\n"

        "1. Utiliza exclusivamente los datos proporcionados por "
        "la herramienta.\n"

        "2. No inventes cifras, modelos, fechas, porcentajes, "
        "estados ni explicaciones técnicas no respaldadas.\n"

        "3. No modifiques, redondees de forma engañosa ni contradigas "
        "los valores obtenidos.\n"

        "4. No afirmes que has buscado en Internet.\n"

        "5. No menciones nombres internos como ToolResult, "
        "ToolRegistry o nombres de clases de Python.\n"

        "6. No ejecutes ni propongas otras herramientas.\n"

        "7. Responde directamente a la pregunta original.\n"

        "8. Mantén un tono cercano y natural, pero serio cuando "
        "la información lo requiera.\n"

        "9. Si los datos muestran un estado normal, puedes indicarlo "
        "brevemente, siempre que sea una conclusión evidente.\n"

        "10. Si no puedes determinar algo con los datos disponibles, "
        "indícalo claramente sin adivinar.\n\n"

        "IDENTIDAD ACTUAL\n\n"

        f"Asistente: {assistant_name}\n"
        f"Usuario activo: {user_name}\n\n"

        "PREGUNTA ORIGINAL DEL USUARIO\n\n"

        f"{user_message}\n\n"

        "HERRAMIENTA UTILIZADA\n\n"

        f"{tool_name}\n\n"

        "RESULTADO TEXTUAL DE LA HERRAMIENTA\n\n"

        f"{tool_message}\n\n"

        "DATOS ESTRUCTURADOS DE LA HERRAMIENTA\n\n"

        f"{serialized_data}\n\n"

        "Redacta ahora la respuesta final como Daxter.\n"

        "No incluyas títulos como «Respuesta» ni expliques "
        "el proceso interno."
    )