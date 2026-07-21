"""Construccion limitada, diversa y trazable del contexto para IA local."""

from dataclasses import dataclass

from knowledge.fragment import KnowledgeFragment


@dataclass(frozen=True, slots=True)
class BuiltKnowledgeContext:
    text: str
    fragments: tuple[KnowledgeFragment, ...]
    truncated: bool


class KnowledgeContextBuilder:
    def __init__(
        self,
        *,
        max_fragments: int = 10,
        max_characters: int = 8_000,
        max_per_source: int = 3,
    ) -> None:
        if min(max_fragments, max_characters, max_per_source) < 1:
            raise ValueError("Los limites de contexto deben ser positivos.")
        self.max_fragments = max_fragments
        self.max_characters = max_characters
        self.max_per_source = max_per_source

    def build(self, fragments: list[KnowledgeFragment]) -> BuiltKnowledgeContext:
        selected: list[KnowledgeFragment] = []
        counts: dict[str, int] = {}
        blocks: list[str] = []
        used = 0
        truncated = False
        for fragment in fragments:
            source_key = f"{fragment.source_type}:{fragment.source_id}"
            if counts.get(source_key, 0) >= self.max_per_source:
                truncated = True
                continue
            label = f"[{fragment.provenance_label} {len(selected) + 1}]"
            block = f"{label} {fragment.title}\n{fragment.content.strip()}"
            remaining = self.max_characters - used
            if remaining <= len(label) + 2:
                truncated = True
                break
            if len(block) > remaining:
                block = block[:remaining].rstrip()
                truncated = True
            blocks.append(block)
            selected.append(fragment)
            counts[source_key] = counts.get(source_key, 0) + 1
            used += len(block) + 2
            if len(selected) >= self.max_fragments:
                truncated = len(fragments) > len(selected)
                break
        return BuiltKnowledgeContext("\n\n".join(blocks), tuple(selected), truncated)
