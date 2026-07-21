"""Controlador determinista de conversación para propuestas de memoria."""

import re

from memory.workflow.detector import normalize


class MemoryWorkflowConversation:
    """Reconoce acciones acotadas y las convierte en capacidades estructuradas."""

    CONFIRM = {"si", "si guardalo", "guardalo", "recuerdalo", "puedes guardarlo", "correcto"}
    REJECT = {"no", "no lo guardes", "dejalo", "olvidalo", "solo te lo estaba contando"}
    ORDINALS = {
        "el primero": 1, "la primera": 1, "el segundo": 2, "la segunda": 2,
        "el tercero": 3, "la tercera": 3, "el cuarto": 4, "la cuarta": 4,
        "el quinto": 5, "la quinta": 5,
        "al primero": 1, "al segundo": 2, "al tercero": 3,
        "al cuarto": 4, "al quinto": 5,
    }
    SENSITIVE_MARKERS = {
        "dni", "nie", "direccion", "telefono", "correo", "iban",
        "nomina", "diagnostico", "historial medico", "medicacion",
    }

    def __init__(self) -> None:
        self.last_memory_results: dict[tuple[str, str | None], list[str]] = {}

    def _execute(self, atlas, capability: str, arguments: dict) -> dict:
        result = atlas.execute_framework_tool(capability, arguments=arguments)
        if not result.success:
            return {"handled": True, "success": False, "message": result.message}
        return {
            "handled": True,
            "success": True,
            "message": result.data.get("message", result.message),
            "data": result.data,
        }

    def handle(self, atlas, text: str) -> dict:
        normalized = re.sub(r"[¿?¡!,.;:]", "", normalize(text)).strip()
        user_id = atlas.get_user()
        session_id = getattr(atlas, "session_id", None)
        pending = atlas.memory_workflow_service.proposals.latest_pending(user_id, session_id)
        state_key = (user_id.casefold(), session_id)

        if pending is not None:
            if pending.operation == "delete_selection":
                selection = self.ORDINALS.get(normalized)
                if selection is None:
                    number = re.search(r"(?:numero |número )?(\d+)$", normalized)
                    if number:
                        selection = int(number.group(1))
                    else:
                        for phrase, value in self.ORDINALS.items():
                            if normalized.endswith(phrase):
                                selection = value
                                break
                if selection is not None:
                    return self._execute(
                        atlas,
                        "memory.select_delete",
                        {
                            "proposal_id": pending.proposal_id,
                            "selection": selection,
                            "session_id": session_id,
                        },
                    )
            if normalized in self.CONFIRM:
                return self._execute(
                    atlas,
                    "memory.confirm",
                    {
                        "proposal_id": pending.proposal_id,
                        "reinforced": False,
                        "session_id": session_id,
                    },
                )
            if normalized in self.REJECT:
                return self._execute(
                    atlas,
                    "memory.reject",
                    {"proposal_id": pending.proposal_id, "session_id": session_id},
                )
            if normalized.startswith(("confirmo expresamente", "si confirmo expresamente")):
                return self._execute(
                    atlas,
                    "memory.confirm",
                    {
                        "proposal_id": pending.proposal_id,
                        "reinforced": True,
                        "session_id": session_id,
                    },
                )
            correction = re.match(r"^(?:si pero |no exactamente |cambialo por |pon )(.+)$", normalized)
            replacement = re.match(r"^si pero cambia (.+) por (.+)$", normalized)
            if replacement:
                content = re.sub(
                    re.escape(replacement.group(1)),
                    replacement.group(2),
                    pending.content,
                    flags=re.IGNORECASE,
                )
                return self._execute(
                    atlas, "memory.update_proposal",
                    {
                        "proposal_id": pending.proposal_id,
                        "content": content,
                        "session_id": session_id,
                    },
                )
            if correction:
                return self._execute(
                    atlas, "memory.update_proposal",
                    {
                        "proposal_id": pending.proposal_id,
                        "content": correction.group(1).strip(),
                        "session_id": session_id,
                    },
                )

        if normalized in {"que propuesta tienes pendiente", "que acabas de proponer"}:
            message = "No hay ninguna propuesta pendiente."
            if pending:
                message = f"La propuesta pendiente es: «{pending.content}»."
            return {"handled": True, "message": message}

        delete_match = re.match(
            r"^(?:olvida|borra|elimina|no recuerdes)(?: lo que recuerdas sobre| mi| ese recuerdo sobre|)\s+(.+)$",
            normalized,
        )
        if delete_match:
            result = self._execute(
                atlas, "memory.propose_delete",
                {"query": delete_match.group(1).strip(" ."), "session_id": session_id},
            )
            candidates = result.get("data", {}).get("candidates", [])
            if candidates:
                result["message"] += "\n" + "\n".join(
                    f"{item['number']}. {item['content']}" for item in candidates
                )
            return result

        change_match = re.match(
            r"^mi (.+?) ya no es (.+?),? ahora es (.+?)[.!]?$",
            normalized,
        )
        if change_match:
            matches = atlas.memory.find_memories(
                owner=user_id,
                query=f"{change_match.group(1)} {change_match.group(2)}",
                limit=2,
            )
            if len(matches) != 1:
                return {
                    "handled": True,
                    "message": "No encuentro un único recuerdo que pueda corregir con seguridad.",
                }
            new_content = f"Mi {change_match.group(1)} es {change_match.group(3)}"
            return self._execute(
                atlas,
                "memory.propose_update",
                {
                    "memory_id": matches[0]["id"],
                    "content": new_content,
                    "text": text,
                    "session_id": session_id,
                },
            )

        read_match = re.match(
            r"^(?:¿?|que )(?:recuerdas|tienes guardado)(?: sobre| de)?\s*(.*?)[?¿]?$",
            normalized,
        )
        if read_match:
            query = read_match.group(1).strip()
            if normalize(query) in {"mi", "sobre mi", "de mi"}:
                query = ""
            explicit_sensitive = any(
                marker in normalize(query) for marker in self.SENSITIVE_MARKERS
            )
            result = self._execute(
                atlas,
                "memory.read",
                {"query": query, "allow_sensitive": explicit_sensitive},
            )
            if not result.get("success", False):
                self.last_memory_results.pop(state_key, None)
                return result
            memories = result.get("data", {}).get("memories", [])
            if memories:
                self.last_memory_results[state_key] = [
                    str(item["id"]) for item in memories
                ]
                result["message"] = "Esto está en tu memoria persistente:\n" + "\n".join(
                    f"- {item['content']} [MEMORIA]" for item in memories
                )
            else:
                self.last_memory_results.pop(state_key, None)
                result["message"] = "No tengo recuerdos guardados que coincidan."
            return result

        if normalized in {"de donde recuerdas eso", "cuando te dije eso", "por que tienes guardado ese dato"}:
            result_ids = self.last_memory_results.get(state_key, [])
            memories = [
                atlas.memory.get_memory_by_id(memory_id, owner=user_id)
                for memory_id in result_ids
            ]
            memories = [item for item in memories if item is not None]
            if not memories:
                return {
                    "handled": True,
                    "message": "No hay un recuerdo concreto en el contexto de esta sesión.",
                }
            details = []
            for memory in memories:
                source = memory.get("source", "memoria anterior al sistema de propuestas")
                date = memory.get("created_at", "fecha desconocida")
                shown = (
                    "[DATO SENSIBLE PROTEGIDO]"
                    if atlas.memory_workflow_service._memory_sensitivity(memory) != "normal"
                    else memory["content"]
                )
                details.append(f"«{shown}»: {source}, registrado el {date}.")
            return {"handled": True, "message": "\n".join(details)}

        candidate = atlas.memory_workflow_service.detector.detect(text)
        if candidate is not None:
            return self._execute(
                atlas, "memory.propose", {"text": text, "session_id": session_id}
            )
        return {"handled": False, "message": ""}
