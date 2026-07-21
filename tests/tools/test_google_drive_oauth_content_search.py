"""Pruebas del cliente API para búsqueda por contenido."""

from tools.google_drive_oauth import (
    GoogleDriveApiClient,
)


def test_query_terms_remove_common_words() -> None:
    terms = GoogleDriveApiClient._query_terms(
        "Dónde hablamos de la memoria persistente"
    )

    assert "memoria" in terms
    assert "persistente" in terms
    assert "donde" not in terms
    assert "de" not in terms


def test_query_terms_are_accent_insensitive() -> None:
    terms = GoogleDriveApiClient._query_terms(
        "autenticación"
    )

    assert terms == ["autenticacion"]
