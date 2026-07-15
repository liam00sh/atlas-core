"""
===============================================================================
Proyecto Atlas
Archivo: tests/test_user_permissions.py

Descripción:
    Contiene las pruebas automáticas relacionadas con los permisos
    entre usuarios del Proyecto Atlas.

    Estas pruebas verifican:

    - Que cada usuario pueda consultar su propio contexto temporal.
    - Que un usuario normal no pueda consultar contextos ajenos.
    - Que el propietario general del sistema pueda administrarlos.
    - Que un usuario sin permiso no pueda borrar contextos ajenos.
    - Que el propietario sí pueda borrar contextos ajenos.
    - Que los contextos se mantengan separados por usuario.
    - Que MemoryManager filtre recuerdos por propietario.
    - Que MemoryManager aplique siempre can_read_memory().
    - Que los recuerdos no autorizados no se devuelvan.
    - Que el perfil y el usuario solicitante lleguen correctamente
      al sistema de control de acceso.

    Las pruebas:

    - No utilizan Ollama.
    - No leen ni modifican memories.json.
    - No cambian los perfiles reales del proyecto.
    - No utilizan información personal real.

    Se emplean objetos falsos y recuerdos controlados.

Ejecución:

    Desde la raíz de atlas_core:

        python -m unittest tests.test_user_permissions -v

    Para ejecutar todas las pruebas:

        python -m unittest discover -s tests -v

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import unittest

from unittest.mock import call
from unittest.mock import patch

from ai.context.context_manager import AIContextManager

from core.atlas_ai import AtlasAIMixin

from memory.memory_manager import MemoryManager


# =============================================================================
# GESTOR DE USUARIOS FALSO
# =============================================================================

class FakeUserManager:
    """
    Gestor mínimo de perfiles utilizado exclusivamente
    por las pruebas de permisos.

    No accede a los perfiles reales de Atlas.
    """

    def __init__(
        self,
        profiles: dict[str, dict],
    ) -> None:
        """
        Inicializa el gestor con perfiles controlados.
        """

        self.profiles = profiles

    def get_profile(
        self,
        user: str,
    ) -> dict:
        """
        Devuelve una copia superficial del perfil solicitado.
        """

        return self.profiles.get(
            user,
            {},
        ).copy()


# =============================================================================
# ATLAS FALSO PARA PROBAR AtlasAIMixin
# =============================================================================

class FakeAtlasWithPermissions(
    AtlasAIMixin,
):
    """
    Implementación mínima de Atlas utilizada para comprobar
    los permisos de los contextos temporales.

    Hereda los métodos reales de AtlasAIMixin, pero sustituye
    el resto de subsistemas por estructuras controladas.
    """

    def __init__(
        self,
    ) -> None:
        """
        Crea dos usuarios:

        Liam:
            Propietario general del sistema.

        Saray:
            Usuario normal sin rol owner.
        """

        self.current_user = "Liam"

        self.users = FakeUserManager(
            profiles={
                "Liam": {
                    "name": "Liam",
                    "roles": [
                        "owner",
                    ],
                    "relationships": {},
                },

                "Saray": {
                    "name": "Saray",
                    "roles": [],
                    "relationships": {},
                },
            }
        )

        self.ai_context_max_messages = 10

        self.ai_contexts: dict[
            str,
            AIContextManager,
        ] = {}

    def get_user(
        self,
    ) -> str:
        """
        Devuelve el usuario activo de la prueba.
        """

        return self.current_user

    def get_name(
        self,
    ) -> str:
        """
        Devuelve el nombre del asistente.
        """

        return "Daxter"

    def set_current_user(
        self,
        user: str,
    ) -> None:
        """
        Cambia el usuario activo dentro del entorno de prueba.
        """

        self.current_user = user


# =============================================================================
# PRUEBAS DE CONTEXTOS TEMPORALES
# =============================================================================

class TestUserContextPermissions(
    unittest.TestCase,
):
    """
    Comprueba los permisos de acceso y administración
    de los contextos temporales de IA.
    """

    def setUp(
        self,
    ) -> None:
        """
        Crea una instancia nueva antes de cada prueba.
        """

        self.atlas = (
            FakeAtlasWithPermissions()
        )

        liam_context = (
            self.atlas._get_ai_context_for_user(
                "Liam"
            )
        )

        liam_context.add_message(
            role="user",
            content="Mensaje privado de Liam.",
        )

        liam_context.add_message(
            role="assistant",
            content="Respuesta para Liam.",
        )

        saray_context = (
            self.atlas._get_ai_context_for_user(
                "Saray"
            )
        )

        saray_context.add_message(
            role="user",
            content="Mensaje privado de Saray.",
        )

        saray_context.add_message(
            role="assistant",
            content="Respuesta para Saray.",
        )

    def test_owner_role_can_manage_other_contexts(
        self,
    ) -> None:
        """
        El usuario con rol owner puede administrar
        contextos de otros usuarios.
        """

        self.atlas.set_current_user(
            "Liam"
        )

        self.assertTrue(
            self.atlas.can_manage_user_contexts()
        )

    def test_normal_user_cannot_manage_other_contexts(
        self,
    ) -> None:
        """
        Un usuario sin rol owner no puede administrar
        contextos ajenos.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        self.assertFalse(
            self.atlas.can_manage_user_contexts()
        )

    def test_user_can_read_own_context(
        self,
    ) -> None:
        """
        Cada usuario puede consultar su propio contexto.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        self.assertIsNotNone(
            messages
        )

        self.assertEqual(
            len(messages),
            2,
        )

        self.assertEqual(
            messages[0]["content"],
            "Mensaje privado de Saray.",
        )

    def test_normal_user_cannot_read_other_context(
        self,
    ) -> None:
        """
        Un usuario normal no puede consultar
        el contexto de otra persona.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Liam"
            )
        )

        self.assertIsNone(
            messages
        )

    def test_owner_can_read_other_context(
        self,
    ) -> None:
        """
        El propietario general puede consultar
        el contexto de otro usuario.
        """

        self.atlas.set_current_user(
            "Liam"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        self.assertIsNotNone(
            messages
        )

        self.assertEqual(
            len(messages),
            2,
        )

        self.assertEqual(
            messages[0]["content"],
            "Mensaje privado de Saray.",
        )

    def test_contexts_are_kept_separate(
        self,
    ) -> None:
        """
        Los mensajes de un usuario no deben aparecer
        dentro del contexto de otro.
        """

        liam_messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Liam"
            )
        )

        saray_messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        liam_contents = {
            message["content"]
            for message in liam_messages
        }

        saray_contents = {
            message["content"]
            for message in saray_messages
        }

        self.assertNotIn(
            "Mensaje privado de Saray.",
            liam_contents,
        )

        self.assertNotIn(
            "Mensaje privado de Liam.",
            saray_contents,
        )

    def test_returned_context_is_a_copy(
        self,
    ) -> None:
        """
        Modificar la lista devuelta no debe cambiar
        el contexto interno original.
        """

        self.atlas.set_current_user(
            "Liam"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        messages[0][
            "content"
        ] = "Contenido modificado externamente."

        original_messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        self.assertEqual(
            original_messages[0]["content"],
            "Mensaje privado de Saray.",
        )

    def test_owner_can_clear_other_context(
        self,
    ) -> None:
        """
        El propietario puede borrar el contexto
        de otro usuario.
        """

        self.atlas.set_current_user(
            "Liam"
        )

        result = (
            self.atlas.clear_ai_context_for_user(
                "Saray"
            )
        )

        self.assertTrue(
            result
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        self.assertEqual(
            messages,
            [],
        )

    def test_normal_user_cannot_clear_other_context(
        self,
    ) -> None:
        """
        Un usuario normal no puede borrar
        el contexto de otra persona.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        result = (
            self.atlas.clear_ai_context_for_user(
                "Liam"
            )
        )

        self.assertFalse(
            result
        )

        self.atlas.set_current_user(
            "Liam"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Liam"
            )
        )

        self.assertEqual(
            len(messages),
            2,
        )

    def test_user_can_clear_own_context(
        self,
    ) -> None:
        """
        Un usuario puede borrar su propio contexto
        aunque no tenga rol owner.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        result = (
            self.atlas.clear_ai_context_for_user(
                "Saray"
            )
        )

        self.assertTrue(
            result
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "Saray"
            )
        )

        self.assertEqual(
            messages,
            [],
        )

    def test_authorized_missing_context_returns_empty_list(
        self,
    ) -> None:
        """
        Consultar un contexto autorizado que todavía no existe
        debe devolver una lista vacía.
        """

        self.atlas.set_current_user(
            "Liam"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "NuevoUsuario"
            )
        )

        self.assertEqual(
            messages,
            [],
        )

    def test_user_name_comparison_is_case_insensitive(
        self,
    ) -> None:
        """
        La comprobación del propietario del contexto
        debe ignorar mayúsculas y minúsculas.
        """

        self.atlas.set_current_user(
            "Saray"
        )

        messages = (
            self.atlas.get_ai_context_messages_for_user(
                "SARAY"
            )
        )

        self.assertIsNotNone(
            messages
        )

        self.assertEqual(
            len(messages),
            2,
        )


# =============================================================================
# PRUEBAS DE ACCESO A RECUERDOS
# =============================================================================

class TestMemoryAccessFiltering(
    unittest.TestCase,
):
    """
    Comprueba que MemoryManager delega correctamente
    las decisiones de acceso en can_read_memory().
    """

    def setUp(
        self,
    ) -> None:
        """
        Crea un MemoryManager sin inicializar archivos.

        Se evita __init__ porque estas pruebas no deben acceder
        a memory/data/memories.json.
        """

        self.manager = (
            MemoryManager.__new__(
                MemoryManager
            )
        )

        self.memories = [
            {
                "id": "liam-public",
                "owner": "Liam",
                "content": "Recuerdo público de Liam.",
                "visibility": "public",
                "created_at": "2026-07-10T10:00:00",
            },
            {
                "id": "liam-private",
                "owner": "Liam",
                "content": "Recuerdo privado de Liam.",
                "visibility": "private",
                "created_at": "2026-07-11T10:00:00",
            },
            {
                "id": "saray-public",
                "owner": "Saray",
                "content": "Recuerdo público de Saray.",
                "visibility": "public",
                "created_at": "2026-07-12T10:00:00",
            },
        ]

        self.manager._load_all_memories = (
            lambda: [
                memory.copy()
                for memory in self.memories
            ]
        )

        self.viewer_profile = {
            "name": "Saray",
            "roles": [],
            "relationships": {},
        }

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_only_requested_owner_memories_are_considered(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        MemoryManager debe filtrar primero por propietario.
        """

        mocked_can_read_memory.return_value = (
            True
        )

        results = (
            self.manager.get_accessible_memories(
                owner="Liam",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        result_ids = {
            memory["id"]
            for memory in results
        }

        self.assertEqual(
            result_ids,
            {
                "liam-public",
                "liam-private",
            },
        )

        self.assertNotIn(
            "saray-public",
            result_ids,
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_denied_memory_is_not_returned(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        Un recuerdo rechazado por can_read_memory()
        no debe aparecer en el resultado.
        """

        def permission_result(
            memory,
            viewer,
            viewer_profile,
        ) -> bool:

            return (
                memory["visibility"]
                == "public"
            )

        mocked_can_read_memory.side_effect = (
            permission_result
        )

        results = (
            self.manager.get_accessible_memories(
                owner="Liam",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["id"],
            "liam-public",
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_all_denied_memories_return_empty_list(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        Si ningún recuerdo está autorizado,
        debe devolverse una lista vacía.
        """

        mocked_can_read_memory.return_value = (
            False
        )

        results = (
            self.manager.get_accessible_memories(
                owner="Liam",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        self.assertEqual(
            results,
            [],
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_all_authorized_memories_are_returned(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        Si todos los recuerdos del propietario están autorizados,
        deben devolverse todos.
        """

        mocked_can_read_memory.return_value = (
            True
        )

        results = (
            self.manager.get_accessible_memories(
                owner="Liam",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        self.assertEqual(
            len(results),
            2,
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_viewer_is_forwarded_to_access_control(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        El nombre del usuario solicitante debe enviarse
        correctamente a can_read_memory().
        """

        mocked_can_read_memory.return_value = (
            True
        )

        self.manager.get_accessible_memories(
            owner="Liam",
            viewer="Saray",
            viewer_profile=self.viewer_profile,
        )

        for current_call in (
            mocked_can_read_memory.call_args_list
        ):

            self.assertEqual(
                current_call.kwargs[
                    "viewer"
                ],
                "Saray",
            )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_profile_is_forwarded_without_changes(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        El perfil debe llegar al control de acceso
        sin ser sustituido ni modificado.
        """

        mocked_can_read_memory.return_value = (
            True
        )

        self.manager.get_accessible_memories(
            owner="Liam",
            viewer="Saray",
            viewer_profile=self.viewer_profile,
        )

        for current_call in (
            mocked_can_read_memory.call_args_list
        ):

            self.assertIs(
                current_call.kwargs[
                    "viewer_profile"
                ],
                self.viewer_profile,
            )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_access_control_receives_each_owner_memory(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        can_read_memory() debe ejecutarse una vez
        por cada recuerdo del propietario solicitado.
        """

        mocked_can_read_memory.return_value = (
            True
        )

        self.manager.get_accessible_memories(
            owner="Liam",
            viewer="Saray",
            viewer_profile=self.viewer_profile,
        )

        self.assertEqual(
            mocked_can_read_memory.call_count,
            2,
        )

        received_ids = {
            current_call.kwargs[
                "memory"
            ]["id"]
            for current_call
            in mocked_can_read_memory.call_args_list
        }

        self.assertEqual(
            received_ids,
            {
                "liam-public",
                "liam-private",
            },
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_owner_comparison_is_case_insensitive(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        La selección por propietario debe ignorar
        mayúsculas y minúsculas.
        """

        mocked_can_read_memory.return_value = (
            True
        )

        results = (
            self.manager.get_accessible_memories(
                owner="LIAM",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        self.assertEqual(
            len(results),
            2,
        )

    @patch(
        "memory.memory_manager.can_read_memory"
    )
    def test_unknown_owner_returns_empty_list(
        self,
        mocked_can_read_memory,
    ) -> None:
        """
        Consultar un propietario inexistente devuelve
        una lista vacía y no llama al control de acceso.
        """

        results = (
            self.manager.get_accessible_memories(
                owner="UsuarioInexistente",
                viewer="Saray",
                viewer_profile=self.viewer_profile,
            )
        )

        self.assertEqual(
            results,
            [],
        )

        mocked_can_read_memory.assert_not_called()


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":

    unittest.main()