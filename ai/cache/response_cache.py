"""
===============================================================================
Proyecto Atlas
Archivo: ai/cache/response_cache.py

Descripción:
    Implementa una caché temporal en memoria.

    Conserva resultados recientes y utilizados frecuentemente
    para evitar repetir operaciones costosas con el modelo local.

    La caché desaparece cuando Atlas se cierra.
===============================================================================
"""


from dataclasses import dataclass
from time import monotonic


@dataclass
class CacheEntry:
    """
    Representa una entrada almacenada en caché.
    """

    value: str
    created_at: float
    last_accessed: float
    ttl_seconds: int
    hits: int = 0


class ResponseCache:
    """
    Caché temporal que favorece entradas recientes
    y utilizadas frecuentemente.
    """

    def __init__(
        self,
        max_entries: int = 100,
    ) -> None:
        """
        Inicializa la caché.

        Parámetros:
            max_entries:
                Número máximo de entradas almacenadas.
        """

        if max_entries < 1:
            raise ValueError(
                "max_entries debe ser mayor que cero."
            )

        self.max_entries = max_entries
        self._entries: dict[str, CacheEntry] = {}

    def get(
        self,
        key: str,
    ) -> str | None:
        """
        Recupera una respuesta almacenada.

        Devuelve None si no existe o ha caducado.
        """

        entry = self._entries.get(
            key
        )

        if entry is None:
            return None

        current_time = monotonic()

        expired = (
            current_time - entry.created_at
            > entry.ttl_seconds
        )

        if expired:

            del self._entries[
                key
            ]

            return None

        entry.hits += 1
        entry.last_accessed = current_time

        return entry.value

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int = 300,
    ) -> None:
        """
        Guarda una respuesta en la caché.
        """

        value = value.strip()

        if not key or not value:
            return

        if len(self._entries) >= self.max_entries:
            self._remove_least_useful_entry()

        current_time = monotonic()

        self._entries[key] = CacheEntry(
            value=value,
            created_at=current_time,
            last_accessed=current_time,
            ttl_seconds=ttl_seconds,
        )

    def _remove_least_useful_entry(
        self,
    ) -> None:
        """
        Elimina la entrada menos utilizada y más antigua.

        Primero se tiene en cuenta el número de usos.
        En caso de empate se elimina la menos reciente.
        """

        if not self._entries:
            return

        key_to_remove = min(
            self._entries,
            key=lambda key: (
                self._entries[key].hits,
                self._entries[key].last_accessed,
            ),
        )

        del self._entries[
            key_to_remove
        ]

    def clear(
        self,
    ) -> None:
        """
        Vacía completamente la caché.
        """

        self._entries.clear()

    def count(
        self,
    ) -> int:
        """
        Devuelve el número de entradas almacenadas.
        """

        return len(
            self._entries
        )

    def remove(
        self,
        key: str,
    ) -> bool:
        """
        Elimina una entrada concreta.
        """

        if key not in self._entries:
            return False

        del self._entries[
            key
        ]

        return True