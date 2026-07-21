"""Deteccion conservadora de contradicciones declaradas por las fuentes."""

from dataclasses import dataclass

from knowledge.fragment import KnowledgeFragment


@dataclass(frozen=True, slots=True)
class KnowledgeConflict:
    fragments: tuple[KnowledgeFragment, ...]
    conflict_type: str
    resolution: str
    requires_confirmation: bool


def detect_conflicts(
    fragments: list[KnowledgeFragment],
) -> list[KnowledgeConflict]:
    """Compara afirmaciones estructuradas; no adivina contradicciones por texto."""

    groups: dict[tuple[str, str], list[KnowledgeFragment]] = {}
    for fragment in fragments:
        subject = str(fragment.metadata.get("subject", "")).casefold().strip()
        predicate = str(fragment.metadata.get("predicate", "")).casefold().strip()
        value = fragment.metadata.get("value")
        if subject and predicate and value is not None:
            groups.setdefault((subject, predicate), []).append(fragment)

    conflicts: list[KnowledgeConflict] = []
    for group in groups.values():
        values = {str(item.metadata["value"]).casefold().strip() for item in group}
        if len(values) < 2:
            continue
        ordered = sorted(group, key=lambda item: (-item.score, not item.verified))
        winner = ordered[0]
        tied = len(ordered) > 1 and (
            ordered[1].verified == winner.verified
            and ordered[1].score == winner.score
        )
        conflicts.append(
            KnowledgeConflict(
                fragments=tuple(ordered),
                conflict_type="incompatible_values",
                resolution=(
                    "requires_confirmation" if tied
                    else f"prioritized:{winner.source_type}:{winner.source_id}"
                ),
                requires_confirmation=tied,
            )
        )
    return conflicts
