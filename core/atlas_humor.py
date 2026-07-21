"""Humor cotidiano clasificado y seguro para Atlas."""
from __future__ import annotations

import random
import re
import unicodedata


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip(" .,!¡!¿?")


class AtlasHumorMixin:
    """Resuelve peticiones de chistes sin depender de la IA generativa."""

    _JOKES = {
        "general": (
            "He ordenado tanto el escritorio que ahora no encuentro ni el desorden.",
            "—¿Qué hace una abeja en el gimnasio? —¡Zum-ba!",
            "—¿Cuál es el colmo de un jardinero? Que siempre lo dejen plantado.",
        ),
        "informatica": (
            "—¿Por qué el ordenador fue al médico? —Porque tenía un virus y no paraba de toser bits.",
            "Un programador entra en una tienda y pide un pan. Su pareja le dice: «Si hay huevos, compra doce». Volvió con doce panes.",
            "—¿Cuántos programadores hacen falta para cambiar una bombilla? —Ninguno: eso es un problema de hardware.",
        ),
        "bomberos": (
            "—¿Cuál es el colmo de un bombero? Apagar la alarma y quedarse dormido.",
            "Un bombero llega tarde al trabajo y dice: «Perdón, se me apagó el despertador».",
            "—¿Por qué los bomberos llevan tirantes? —Porque los pantalones solos no suben.",
        ),
        "maestras": (
            "La maestra pregunta: «¿Quién puede decirme una palabra con muchas letras?». Y el alumno responde: «El abecedario».",
            "—Profe, ¿me castigaría por algo que no he hecho? —Claro que no. —Qué bien, porque no he hecho los deberes.",
            "La maestra dice: «Poned un ejemplo de paciencia». Un alumno responde: «Esperar a que termine de corregir los exámenes».",
        ),
        "humor_negro_suave": (
            "Mi planta y yo tenemos algo en común: las dos fingimos estar bien cuando alguien nos echa agua.",
            "El optimista ve luz al final del túnel. El pesimista ve oscuridad. El maquinista ve a dos personas en las vías.",
            "Quise hacer una dieta estricta, pero el chocolate me recordó que la vida ya es bastante dura.",
        ),
        "prejuicios": (
            "Uno dice: «Yo no tengo prejuicios». El otro responde: «Perfecto, entonces ya puedes empezar a escuchar a la gente antes de etiquetarla».",
            "El machista entra en una biblioteca y pregunta dónde están los libros de superioridad masculina. La bibliotecaria responde: «En ciencia ficción».",
            "Un racista intenta contar un chiste. Nadie se ríe. Resulta que el problema no era el público, era el prejuicio.",
        ),
    }

    @classmethod
    def _humor_category(cls, text: str) -> str | None:
        normalized = _plain(text)
        if "chiste" not in normalized and "hazme reir" not in normalized:
            return None
        if any(word in normalized for word in ("informatic", "programador", "ordenador", "linux", "windows")):
            return "informatica"
        if "bombero" in normalized:
            return "bomberos"
        if any(word in normalized for word in ("maestra", "maestro", "profe", "profesor")):
            return "maestras"
        if any(word in normalized for word in ("humor negro", "chiste negro")):
            return "humor_negro_suave"
        if any(word in normalized for word in ("racista", "negros", "negro", "chinos", "machista", "mujeres")):
            return "prejuicios"
        return "general"

    def _handle_classified_humor(self, text: str) -> bool:
        category = self._humor_category(text)
        if category is None:
            return False
        options = self._JOKES[category]
        previous = getattr(self, "_last_atlas_joke", None)
        candidates = [joke for joke in options if joke != previous] or list(options)
        joke = random.choice(candidates)
        self._last_atlas_joke = joke
        if category == "prejuicios":
            print("Puedo hacer humor suave sobre prejuicios sin atacar a un grupo. Aquí va:")
            print()
        print(joke)
        return True
