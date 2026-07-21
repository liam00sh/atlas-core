"""Orquestacion de recuperacion, contexto, proveedor local y fuentes."""

from dataclasses import asdict, dataclass
from typing import Any

from knowledge.context_builder import KnowledgeContextBuilder
from knowledge.retriever import KnowledgeRetriever


@dataclass(frozen=True, slots=True)
class KnowledgeAnswer:
    answer: str
    sources: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    insufficient: bool = False


class KnowledgeService:
    def __init__(self, retriever: KnowledgeRetriever, provider: Any = None, context_builder: KnowledgeContextBuilder | None = None):
        self.retriever = retriever
        self.provider = provider
        self.context_builder = context_builder or KnowledgeContextBuilder()

    def answer(self, question: str, *, user_id: str, allow_sensitive: bool = False, has_sensitive_permission: bool = False, drive_scope: dict | None = None) -> KnowledgeAnswer:
        fragments = self.retriever.retrieve(
            question,
            user_id=user_id,
            allow_sensitive=allow_sensitive,
            has_sensitive_permission=has_sensitive_permission,
            drive_scope=drive_scope,
        )
        if not fragments:
            return KnowledgeAnswer("No hay informacion suficiente en las fuentes autorizadas.", (), (), True)
        built = self.context_builder.build(fragments)
        conflicts = tuple(
            {
                "type": conflict.conflict_type,
                "resolution": conflict.resolution,
                "requires_confirmation": conflict.requires_confirmation,
                "source_ids": [item.source_id for item in conflict.fragments],
            }
            for conflict in self.retriever.last_conflicts
        )
        sources = tuple(
            asdict(item)
            for item in built.fragments
        )
        try:
            provider_available = (
                self.provider is not None
                and self.provider.is_available()
            )
        except Exception:
            provider_available = False

        if not provider_available:
            return KnowledgeAnswer(
                "El proveedor local no esta disponible para redactar la respuesta.",
                sources,
                conflicts,
                True,
            )
        prompt = (
            "Responde solo con el conocimiento proporcionado. Conserva la procedencia "
            "con sus etiquetas, avisa de contradicciones y reconoce cualquier insuficiencia.\n\n"
            f"Pregunta: {question.strip()}\n\nConocimiento:\n{built.text}"
        )
        try:
            answer = self.provider.generate(prompt).strip()
        except Exception:
            return KnowledgeAnswer(
                "El proveedor local no esta disponible para redactar la respuesta.",
                sources,
                conflicts,
                True,
            )

        if not answer:
            return KnowledgeAnswer(
                "El proveedor local no ha generado una respuesta util.",
                sources,
                conflicts,
                True,
            )
        if conflicts:
            answer += "\n\nAdvertencia: se ha detectado informacion contradictoria entre fuentes."
        return KnowledgeAnswer(answer, sources, conflicts)
