from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Capability:
    """Identificador normalizado de una capacidad ofrecida por una herramienta."""

    name: str

    def __post_init__(self) -> None:
        normalized = self.name.strip().lower()
        if not normalized:
            raise ValueError("La capacidad no puede estar vacía.")
        object.__setattr__(self, "name", normalized)

    def __str__(self) -> str:
        return self.name
