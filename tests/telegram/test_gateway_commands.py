from __future__ import annotations

import pytest
import threading
import time

from telegram_interface.audit import TelegramAuditLogger
from telegram_interface.core_adapter import CallableCoreAdapter
from telegram_interface.gateway import TelegramGateway
from telegram_interface.session_manager import TelegramSessionManager

from tests.telegram.conftest import link_user, make_message


def test_start_unknown_produces_temporary_code_without_private_data(gateway, storage):
    response = gateway.handle(make_message("/start"))
    assert "Atlas es privado" in response.text
    assert "Liam" not in response.text
    assert storage.section("link_codes")


def test_unlinked_help_only_lists_public_commands(gateway):
    text = gateway.handle(make_message("/help")).text
    assert "/start" in text
    assert "/daxter" not in text
    assert "/unlink" not in text


@pytest.mark.parametrize("command", ["/assistant", "/daxter", "/coco", "/unlink"])
def test_private_commands_rejected_for_unlinked(gateway, command):
    assert "requiere una cuenta vinculada" in gateway.handle(make_message(command)).text


def test_unlinked_normal_text_never_reaches_core(config, storage, linker, tmp_path):
    calls = []
    gateway = TelegramGateway(
        config=config,
        linker=linker,
        sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(lambda text, context: calls.append((text, context))),
        audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
    )
    try:
        response = gateway.handle(make_message("Consulta mi memoria"))
        assert "no esta vinculada" in response.text
        assert calls == []
    finally:
        gateway.close()


def test_linked_start_status_whoami_and_assistant(gateway, linker):
    link_user(linker)
    assert "vinculado a Liam" in gateway.handle(make_message("/start")).text
    assert "Usuario: Liam" in gateway.handle(make_message("/status")).text
    assert "usuario Liam" in gateway.handle(make_message("/whoami")).text
    assert "Daxter" in gateway.handle(make_message("/assistant")).text


def test_normal_message_uses_linked_user_context(gateway, linker):
    link_user(linker)
    assert gateway.handle(make_message("hola")).text == "Liam:hola"


def test_personalities_are_independent(gateway, linker, personalities):
    link_user(linker, user_id="100", chat_id="200", atlas_user="Liam")
    link_user(linker, user_id="101", chat_id="201", atlas_user="Saray")
    assert "Coco" in gateway.handle(make_message("/coco", user_id="100", chat_id="200")).text
    assert personalities == {"Liam": "coco", "Saray": "coco"}
    assert "Coco" in gateway.handle(make_message("/assistant", user_id="101", chat_id="201")).text
    gateway.handle(make_message("/daxter", user_id="100", chat_id="200"))
    assert personalities == {"Liam": "daxter", "Saray": "coco"}


def test_unlink_requires_explicit_confirmation(gateway, linker):
    link_user(linker)
    gateway.handle(make_message("/unlink"))
    assert linker.get_account("100")["state"] == "linked"
    response = gateway.handle(make_message("/unlink_confirm"))
    assert response.close_session is True
    assert linker.get_account("100")["state"] == "unlinked"


def test_cancel_clears_unlink_without_unlinking(gateway, linker):
    link_user(linker)
    gateway.handle(make_message("/unlink"))
    assert "cancelada" in gateway.handle(make_message("/cancel")).text
    assert linker.get_account("100")["state"] == "linked"


def test_unknown_command_is_controlled(gateway):
    assert "desconocido" in gateway.handle(make_message("/root_access")).text


def test_empty_and_long_messages_are_controlled(gateway, linker, config):
    link_user(linker)
    assert "Escribe un mensaje" in gateway.handle(make_message("   ")).text
    assert "demasiado largo" in gateway.handle(make_message("x" * (config.max_input_characters + 1))).text


def test_group_messages_are_rejected(gateway):
    message = make_message("hola")
    message = type(message)(
        message.update_id, message.message_id, message.user, message.text,
        timestamp=message.timestamp, chat_type="group"
    )
    assert "solo admite conversaciones privadas" in gateway.handle(message).text


def test_channel_permission_can_restrict_linked_user(config, storage, linker, tmp_path):
    link_user(linker)
    gateway = TelegramGateway(
        config=config,
        linker=linker,
        sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(lambda _text, _context: "forbidden"),
        audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"memory.read"},
    )
    try:
        assert "no tiene permiso" in gateway.handle(make_message("privado")).text
    finally:
        gateway.close()


def test_core_exception_returns_safe_error(config, storage, linker, tmp_path):
    link_user(linker)
    def fail(_text, _context):
        raise RuntimeError("private prompt")
    gateway = TelegramGateway(
        config=config, linker=linker, sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(fail), audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"telegram.use"},
    )
    try:
        response = gateway.handle(make_message("mensaje secreto"))
        assert response.text == "Atlas no pudo procesar el mensaje de forma segura."
        assert "private prompt" not in response.text
    finally:
        gateway.close()


def test_two_messages_same_session_never_run_core_simultaneously(config, storage, linker, tmp_path):
    link_user(linker)
    active = 0
    maximum = 0
    guard = threading.Lock()
    def handler(text, _context):
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.03)
        with guard:
            active -= 1
        return text
    gateway = TelegramGateway(
        config=config, linker=linker, sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(handler), audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"telegram.use"},
    )
    try:
        threads = [threading.Thread(target=gateway.handle, args=(make_message(str(i), update_id=i),)) for i in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert maximum == 1
    finally:
        gateway.close()


def test_two_users_have_independent_sessions(config, storage, linker, tmp_path):
    link_user(linker, user_id="100", chat_id="200", atlas_user="Liam")
    link_user(linker, user_id="101", chat_id="201", atlas_user="Saray")
    seen = []
    def handler(text, context):
        seen.append((context.atlas_user_id, context.session_id, text))
        return "ok"
    gateway = TelegramGateway(
        config=config, linker=linker, sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(handler), audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"telegram.use"},
    )
    try:
        gateway.handle(make_message("uno", user_id="100", chat_id="200"))
        gateway.handle(make_message("dos", user_id="101", chat_id="201"))
        assert seen[0][0] == "Liam" and seen[1][0] == "Saray"
        assert seen[0][1] != seen[1][1]
    finally:
        gateway.close()


def test_repeated_core_errors_create_short_per_session_cooldown(config, storage, linker, tmp_path):
    link_user(linker)
    calls = []
    def fail(_text, _context):
        calls.append(1)
        raise RuntimeError("safe")
    gateway = TelegramGateway(
        config=config, linker=linker, sessions=TelegramSessionManager(storage),
        core=CallableCoreAdapter(fail), audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"telegram.use"}, clock=lambda: 100.0,
    )
    try:
        for index in range(3):
            assert "no pudo procesar" in gateway.handle(make_message("x", update_id=index)).text
        assert "varios errores" in gateway.handle(make_message("x", update_id=4)).text
        assert len(calls) == 3
    finally:
        gateway.close()
