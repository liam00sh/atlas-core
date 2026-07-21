"""Comprensión interactiva, aclaraciones e interés humano para Atlas."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import threading
from typing import Any
import unicodedata


class UnderstandingStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {"version": 1, "users": {}}
        return payload if isinstance(payload, dict) else {"version": 1, "users": {}}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._load())

    def update(self, mutator):
        with self._lock:
            payload = self._load()
            result = mutator(payload)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return result


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(ch for ch in normalized if unicodedata.category(ch) != "Mn" and (ch.isalnum() or ch.isspace())).split())


class AtlasUnderstandingMixin:
    """Ayuda a deducir necesidades sin convertir hipótesis en hechos."""

    def _understanding_bootstrap(self) -> None:
        if getattr(self, "_understanding_ready", False):
            return
        root = Path(__file__).resolve().parents[1]
        self.understanding_storage = UnderstandingStorage(root / "data" / "conversation" / "understanding.json")
        self._understanding_ready = True

    def _understanding_user(self) -> str:
        getter = getattr(self, "_get_current_conversation_user", None)
        return str(getter()) if callable(getter) else str(self.get_user())

    def _uprint(self, message: str) -> None:
        print()
        print(message)

    def _user_record(self, payload: dict[str, Any], owner: str) -> dict[str, Any]:
        return payload.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner})

    def _set_pending(self, owner: str, kind: str, original: str, question: str, hypotheses: list[str]) -> None:
        def mutate(payload: dict[str, Any]) -> None:
            user = self._user_record(payload, owner)
            user["pending_clarification"] = {
                "kind": kind,
                "original": original,
                "question": question,
                "hypotheses": hypotheses,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.understanding_storage.update(mutate)

    def _handle_pending_understanding(self, text: str) -> bool:
        self._understanding_bootstrap()
        owner = self._understanding_user()
        pending = self.understanding_storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("pending_clarification")
        if not isinstance(pending, dict):
            return False
        plain = _plain(text)
        if plain in {"cancelar", "dejalo", "da igual", "olvidalo"}:
            self._clear_pending(owner)
            self._uprint("De acuerdo, lo dejamos ahí.")
            return True
        # Una respuesta breve a la pregunta aclaratoria se combina con el problema original.
        if len(text.split()) <= 18 or any(word in plain for word in ("sale", "dice", "espacio", "permiso", "memoria", "error", "pantalla")):
            original = str(pending.get("original", ""))
            kind = str(pending.get("kind", "problema"))
            self._clear_pending(owner)
            prompt = (
                "Ayuda a resolver el problema usando solo lo que el usuario ha contado. "
                "No afirmes una causa si no está confirmada. Empieza por la comprobación más sencilla, "
                "da como máximo tres pasos y termina con una pregunta breve para comprobar el resultado.\n"
                f"Problema inicial: {original}\nRespuesta aclaratoria: {text}\nTipo: {kind}"
            )
            provider = getattr(self, "ai_provider", None)
            if provider is not None:
                try:
                    answer = str(provider.generate(prompt)).strip()
                except Exception:
                    answer = "Gracias. Empecemos por comprobar el espacio libre y el mensaje exacto que aparece."
            else:
                answer = "Gracias. Empecemos por la comprobación más sencilla. ¿Puedes decirme el mensaje exacto que aparece?"
            self._uprint(answer)
            return True
        return False

    def _clear_pending(self, owner: str) -> None:
        def mutate(payload: dict[str, Any]) -> None:
            self._user_record(payload, owner).pop("pending_clarification", None)
        self.understanding_storage.update(mutate)

    def _remember_wellbeing(self, owner: str, body_part: str, symptom: str) -> None:
        now = datetime.now()
        def mutate(payload: dict[str, Any]) -> None:
            user = self._user_record(payload, owner)
            threads = user.setdefault("wellbeing_threads", [])
            threads.append({
                "body_part": body_part,
                "symptom": symptom,
                "mentioned_at": now.isoformat(timespec="seconds"),
                "follow_up_after": (now + timedelta(minutes=30)).isoformat(timespec="seconds"),
                "asked": False,
                "closed": False,
            })
            del threads[:-20]
        self.understanding_storage.update(mutate)

    def _emit_due_wellbeing_followup(self, current_text: str) -> None:
        self._understanding_bootstrap()
        owner = self._understanding_user()
        plain = _plain(current_text)
        if any(word in plain for word in ("ojo", "dolor", "molesta", "mejor", "peor")):
            return
        snapshot = self.understanding_storage.snapshot()
        threads = snapshot.get("users", {}).get(owner.casefold(), {}).get("wellbeing_threads", [])
        now = datetime.now()
        due_index = None
        due = None
        for index, item in enumerate(threads):
            if item.get("asked") or item.get("closed"):
                continue
            try:
                follow = datetime.fromisoformat(str(item.get("follow_up_after")))
            except (TypeError, ValueError):
                continue
            if follow <= now:
                due_index, due = index, item
                break
        if due is None:
            return
        def mutate(payload: dict[str, Any]) -> None:
            payload["users"][owner.casefold()]["wellbeing_threads"][due_index]["asked"] = True
        self.understanding_storage.update(mutate)
        body = str(due.get("body_part", "molestia"))
        self._uprint(f"Por cierto, ¿cómo sigue lo del {body}? ¿Está mejor, igual o peor?")

    def _handle_human_understanding(self, text: str) -> bool:
        self._understanding_bootstrap()
        owner = self._understanding_user()
        plain = _plain(text)

        # Respuestas a seguimiento de bienestar.
        if re.search(r"\b(?:esta|estoy)\s+(?:mejor|igual|peor)\b", plain) and len(plain.split()) <= 8:
            status = "mejor" if "mejor" in plain else "peor" if "peor" in plain else "igual"
            def mutate(payload: dict[str, Any]) -> None:
                threads = self._user_record(payload, owner).setdefault("wellbeing_threads", [])
                for item in reversed(threads):
                    if item.get("asked") and not item.get("closed"):
                        item["status"] = status
                        item["closed"] = status == "mejor"
                        item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                        break
            self.understanding_storage.update(mutate)
            if status == "mejor":
                self._uprint("Me alegro de que esté mejor 🙂")
            elif status == "igual":
                self._uprint("Vaya. Si sigue igual, vigílalo y dime si aparece algún síntoma nuevo.")
            else:
                self._uprint("Siento que esté peor. ¿Tienes dolor intenso, pérdida de visión, mucha inflamación o secreción? Si aparece alguno, conviene consultar cuanto antes.")
            return True

        symptom = re.search(r"\bme\s+(?:duele|molesta|pica|escuece)\s+(?:el|la|los|las)?\s*([a-zñ]+)", plain)
        if symptom:
            body = symptom.group(1)
            self._remember_wellbeing(owner, body, symptom.group(0))
            self._uprint(f"Vaya, siento que te moleste el {body}. ¿Desde cuándo te pasa y tienes algún otro síntoma?")
            return True

        # Capacidades explicadas de forma conversacional.
        if "descargar un documento" in plain:
            self._uprint("Puedo ayudarte a localizar y descargar un documento cuando esté conectado a una fuente compatible. ¿De dónde quieres descargarlo: Drive, una web, Telegram u otro sitio?")
            return True
        if "desde whatsapp" in plain and any(word in plain for word in ("foto", "fotos", "camara")):
            self._uprint("Desde aquí no puedo abrir WhatsApp ni pulsar la cámara por ti, pero sí puedo guiarte paso a paso. ¿Quieres hacer una foto dentro de un chat o enviar una que ya tienes?")
            return True

        # Problemas tecnológicos narrados con rodeos: extraer necesidad y preguntar una cosa.
        mobile_problem = any(word in plain for word in ("movil", "telefono", "camara", "foto", "whatsapp", "pantalla", "aplicacion", "app"))
        distress = any(phrase in plain for phrase in ("no funciona", "va fatal", "no puedo", "sale un mensaje", "mensaje raro", "antes funcionaba", "ya no se"))
        if mobile_problem and distress:
            if any(word in plain for word in ("camara", "foto")):
                hypotheses = ["almacenamiento lleno", "permiso de cámara", "otra aplicación usa la cámara", "fallo de la aplicación"]
                question = "¿Qué mensaje aparece exactamente al intentar hacer la foto?"
                kind = "camera_problem"
            elif "va fatal" in plain or "lento" in plain:
                hypotheses = ["poco espacio libre", "muchas aplicaciones abiertas", "actualización pendiente", "batería o temperatura"]
                question = "¿Lo notas lento en todo el móvil o solo en una aplicación?"
                kind = "slow_phone"
            else:
                hypotheses = ["permiso", "espacio", "conexión", "fallo de aplicación"]
                question = "¿Qué estabas intentando hacer y qué mensaje te aparece?"
                kind = "generic_mobile_problem"
            self._set_pending(owner, kind, text, question, hypotheses)
            self._uprint(question)
            return True

        # Peticiones demasiado vagas: una única pregunta que reduzca incertidumbre.
        if plain in {"mi movil va fatal", "esto no funciona", "no puedo hacerlo", "ayudame con el movil", "tengo un problema"}:
            self._set_pending(owner, "vague_problem", text, "¿Qué intentabas hacer justo antes de que fallara?", [])
            self._uprint("¿Qué intentabas hacer justo antes de que fallara?")
            return True

        return False
