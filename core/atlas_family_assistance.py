"""Asistencia cotidiana y guías familiares para Proyecto Atlas.

El módulo prioriza ayuda interactiva, accesibilidad, enlaces y saludos útiles.
No ejecuta acciones sensibles ni navega automáticamente sin una petición clara.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlparse


_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


class AtlasFamilyAssistanceMixin:
    def _family_assistance_state(self) -> dict:
        state = getattr(self, "_family_assistance_runtime", None)
        if state is None:
            state = {"pending_url": None, "guide": None}
            self._family_assistance_runtime = state
        return state

    @staticmethod
    def _family_print(text: str) -> None:
        print()
        print(text)

    def _handle_family_assistance(self, text: str) -> bool:
        raw = " ".join(text.split()).strip()
        normalized = raw.casefold().strip(" .,!¡¿?")
        state = self._family_assistance_state()

        if normalized in {"repite", "repitelo", "repítelo", "otra vez"}:
            previous = state.get("last_help")
            self._family_print(previous or "Todavía no tengo una instrucción anterior que repetir.")
            return True

        if normalized in {"explicamelo mas facil", "explícamelo más fácil", "mas facil", "más fácil"}:
            self._family_print(
                "Claro. Dime qué parte te resulta difícil y te la explicaré con una sola instrucción cada vez."
            )
            return True

        if normalized in {"ya", "hecho", "listo", "ya esta", "ya está"} and state.get("guide"):
            guide = state["guide"]
            index = int(guide.get("index", 0)) + 1
            steps = list(guide.get("steps", []))
            if index >= len(steps):
                state["guide"] = None
                self._family_print("Perfecto, hemos terminado. ¿Ha funcionado?")
            else:
                guide["index"] = index
                answer = steps[index]
                state["last_help"] = answer
                self._family_print(answer)
            return True

        if normalized.startswith("no me aparece") and state.get("guide"):
            self._family_print("No pasa nada. Dime qué opciones ves en pantalla y continuamos desde ahí.")
            return True

        urls = _URL_RE.findall(raw)
        if urls:
            url = urls[0].rstrip(".,)")
            host = urlparse(url).netloc.removeprefix("www.") or "esa página"
            state["pending_url"] = url
            self._family_print(
                f"He reconocido un enlace de {host}. Puedo resumirlo, explicarte para qué sirve, "
                "comparar su información o revisar señales básicas de riesgo. ¿Qué necesitas hacer con él?"
            )
            return True

        if state.get("pending_url") and any(word in normalized for word in ("resume", "resumelo", "resúmelo", "revisa", "es seguro", "sospechoso", "compara")):
            url = state.pop("pending_url")
            self._family_print(
                f"Voy a revisar {url}. No iniciaré sesión, aceptaré condiciones ni pulsaré nada por ti. "
                "Usaré únicamente información pública y te indicaré las fuentes consultadas."
            )
            # La revisión real continúa por el flujo de Internet existente.
            return False

        if normalized in {"buenos dias", "buenos días"}:
            self._family_print(self._build_daily_briefing(morning=True))
            return True

        if normalized in {"buenas noches"}:
            self._family_print(self._build_daily_briefing(morning=False))
            return True

        if any(phrase in normalized for phrase in (
            "como cambio el fondo", "cómo cambio el fondo", "exportar a pdf desde excel",
            "guardar excel en pdf", "no funciona una pagina", "no funciona una página",
            "no funciona una app", "me sale una cosa rara",
        )):
            return self._start_basic_guide(normalized, state)

        if normalized.startswith("no puedo"):
            self._family_print(
                "Quizá no pueda hacerlo directamente por ti, pero sí puedo guiarte paso a paso. "
                "Dime qué estabas intentando hacer y qué aparece en pantalla."
            )
            return True

        return False

    def _start_basic_guide(self, normalized: str, state: dict) -> bool:
        if "fondo" in normalized:
            steps = [
                "Haz clic con el botón derecho en una zona vacía del escritorio.",
                "Pulsa «Personalizar».",
                "Entra en «Fondo» y elige una imagen. Avísame cuando estés dentro de Personalizar.",
            ]
        elif "pdf" in normalized and "excel" in normalized:
            steps = [
                "En Excel, abre el menú «Archivo».",
                "Pulsa «Exportar» o «Guardar como».",
                "Elige PDF como tipo de archivo, revisa la carpeta y pulsa Guardar.",
            ]
        else:
            self._family_print("¿Lo estás haciendo desde el móvil o desde el ordenador?")
            return True
        state["guide"] = {"steps": steps, "index": 0}
        state["last_help"] = steps[0]
        self._family_print(steps[0])
        return True

    def _build_daily_briefing(self, *, morning: bool) -> str:
        user = self.get_user()
        now = datetime.now()
        greeting = "Buenos días" if morning else "Buenas noches"
        sections = [f"{greeting}, {user} 😊"]
        agenda = self._read_daily_agenda(user, now.date().isoformat())
        if morning:
            sections.append(
                "Puedo darte la previsión del tiempo de tu ubicación guardada cuando la consulta meteorológica esté configurada. "
                "No usaré una ubicación nueva sin tu permiso."
            )
            sections.append(agenda or "Hoy no encuentro tareas o recordatorios pendientes guardados.")
            sections.append("También revisaré cumpleaños y festivos cuando estén registrados en tu calendario o perfil.")
        else:
            sections.append(agenda or "No encuentro tareas pendientes para cerrar hoy.")
            sections.append(
                "Puedo recordarte el turno de mañana cuando esté guardado. Las alarmas del teléfono se añadirán en una integración posterior."
            )
            sections.append("Descansa. Mañana retomamos lo que haya quedado pendiente.")
        return "\n\n".join(sections)

    @staticmethod
    def _read_daily_agenda(user: str, day: str) -> str:
        root = Path(__file__).resolve().parents[1]
        path = root / "data" / "daily_life" / "state.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        reminders = data.get("reminders", []) if isinstance(data, dict) else []
        pending = []
        for item in reminders if isinstance(reminders, list) else []:
            if not isinstance(item, dict):
                continue
            if str(item.get("owner", "")).casefold() != user.casefold():
                continue
            due = str(item.get("due_at", ""))
            if due.startswith(day) and item.get("status", "pending") == "pending":
                pending.append(str(item.get("message", "recordatorio")))
        if not pending:
            return ""
        return "Tienes pendiente hoy:\n" + "\n".join(f"• {item}" for item in pending[:8])
