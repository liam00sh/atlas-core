"""Cálculos cotidianos seguros sin eval libre."""
from __future__ import annotations

import ast
import operator
import re


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Expresión no permitida")


def calculate_from_text(text: str) -> str | None:
    plain = " ".join(text.casefold().replace(",", ".").split())
    discount = re.search(r"(?:cuesta|vale)\s+(\d+(?:\.\d+)?)\s*(?:€|euros?)?.*?(\d+(?:\.\d+)?)\s*%\s+de\s+descuento", plain)
    if discount:
        price, percent = map(float, discount.groups())
        result = price * (1 - percent / 100)
        return f"Con un {percent:g} % de descuento, se queda en {result:.2f} €.".replace(".", ",")

    glasses = re.search(r"cu[aá]ntos?\s+mililitros\s+son\s+(\d+(?:\.\d+)?)\s+vasos?", plain)
    if glasses:
        count = float(glasses.group(1))
        ml = count * 250
        return f"Tomando un vaso estándar de 250 ml, son aproximadamente {ml:g} ml."

    expression = plain
    number_words = {
        "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
        "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
        "ocho": "8", "nueve": "9", "diez": "10",
    }
    for word, digit in number_words.items():
        expression = re.sub(rf"\b{word}\b", digit, expression)
    replacements = {
        "cuanto son": "", "cuánto son": "", "cuanto es": "", "cuánto es": "",
        "euros": "", "euro": "", "entre": "/", "por": "*", "mas": "+", "más": "+", "menos": "-",
    }
    for source, target in replacements.items():
        expression = expression.replace(source, target)
    expression = re.sub(r"[^0-9.+\-*/() ]", "", expression).strip()
    if not expression or not any(op in expression for op in "+-*/"):
        return None
    try:
        value = _eval(ast.parse(expression, mode="eval"))
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"El resultado es {value}."
