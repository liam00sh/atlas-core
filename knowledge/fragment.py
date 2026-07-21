"""Modelos neutrales compartidos por todas las fuentes de conocimiento."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeFragment:
    """Unidad recuperada sin alterar ni duplicar su fuente original."""

    source_type: str
    source_id: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.source_type.strip():
            raise ValueError("El tipo de fuente no puede estar vacio.")
        if not self.source_id.strip():
            raise ValueError("El identificador de fuente no puede estar vacio.")
        if not self.content.strip():
            raise ValueError("El contenido no puede estar vacio.")
        object.__setattr__(self, "score", float(self.score))

    @property
    def provenance_label(self) -> str:
        labels = {
            "memory": "MEMORIA",
            "person": "PERSONA VERIFICADA" if self.verified else "PERSONA",
            "relationship": "RELACION VERIFICADA" if self.verified else "RELACION",
            "drive_document": "DOCUMENTO",
            "semantic_chunk": "FRAGMENTO SEMANTICO",
            "system_fact": "HECHO DEL SISTEMA",
            "conversation_context": "CONTEXTO",
        }
        return labels.get(self.source_type, self.source_type.upper())

    @property
    def deduplication_key(self) -> str:
        text = " ".join(self.content.casefold().split())
        return f"{self.source_id}:{text}"
