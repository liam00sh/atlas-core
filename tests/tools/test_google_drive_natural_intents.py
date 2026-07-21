from tools.google_drive_conversation import (
    GoogleDriveConversationController,
)


def test_natural_drive_list_intents() -> None:
    controller = GoogleDriveConversationController()

    assert controller._is_drive_list_intent(
        "mostrar el listado de Drive"
    )
    assert controller._is_drive_list_intent(
        "enséñame qué archivos hay en Drive"
    )
    assert controller._is_drive_list_intent(
        "quiero ver el contenido de Atlas Project"
    )


def test_natural_index_status_intents() -> None:
    controller = GoogleDriveConversationController()

    assert controller._is_index_status_intent(
        "muéstrame cómo está el índice de Drive"
    )
    assert controller._is_index_status_intent(
        "dime el estado de la indexación"
    )


def test_semantic_intents() -> None:
    controller = GoogleDriveConversationController()

    assert controller._is_semantic_sync_intent(
        "actualiza el índice semántico de Drive"
    )
    assert controller._is_semantic_status_intent(
        "muéstrame el estado semántico"
    )
    assert controller._semantic_query(
        "busca semánticamente en Drive cómo funciona la memoria"
    ) == "cómo funciona la memoria"
