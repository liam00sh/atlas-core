from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from telegram_interface.identity_linker import TelegramLinkError
from telegram_interface.models import TelegramUser


def test_unknown_account_is_unlinked(linker):
    assert linker.get_account("404")["state"] == "unlinked"


def test_code_is_hashed_and_account_pending(linker, storage):
    code = linker.request_code(TelegramUser("100", "200", username="liam"))
    payload = storage.snapshot()
    serialized = str(payload)
    assert code not in serialized
    assert payload["accounts"]["100"]["state"] == "link_pending"


def test_confirmation_links_by_id_not_username(linker):
    code = linker.request_code(TelegramUser("100", "200", username="Saray"))
    linker.confirm_code(code, "Liam", user_exists=lambda value: value == "Liam")
    account = linker.get_account("100")
    assert account["atlas_user_id"] == "Liam"
    assert account["state"] == "linked"


def test_code_is_one_use(linker):
    code = linker.request_code(TelegramUser("100", "200"))
    linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    with pytest.raises(TelegramLinkError) as caught:
        linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    assert caught.value.code == "invalid_link_code"


def test_expired_code_is_rejected(linker, storage):
    code = linker.request_code(TelegramUser("100", "200"))
    storage.update(lambda data: data["link_codes"][next(iter(data["link_codes"]))].update(
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    ))
    with pytest.raises(TelegramLinkError) as caught:
        linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    assert caught.value.code == "expired_link_code"


def test_wrong_code_reduces_attempts_and_eventually_blocks(linker, storage):
    code = linker.request_code(TelegramUser("100", "200"))
    wrong_code = code[:3] + ("A" * 7 if code[3:] != "A" * 7 else "B" * 7)
    for _ in range(5):
        with pytest.raises(TelegramLinkError):
            linker.confirm_code(wrong_code, "Liam", user_exists=lambda _: True)
    proposal = next(iter(storage.section("link_codes").values()))
    assert proposal["state"] == "blocked"
    assert set(proposal) == {"state", "closed_at"}
    assert linker.get_account("100")["state"] == "blocked"


def test_wrong_prefix_does_not_consume_another_accounts_attempts(linker, storage):
    code = linker.request_code(TelegramUser("100", "200"))
    with pytest.raises(TelegramLinkError):
        linker.confirm_code("ZZZAAAAAAA", "Liam", user_exists=lambda _: True)
    proposal = next(iter(storage.section("link_codes").values()))
    assert proposal["attempts_left"] == 5
    assert code not in str(storage.snapshot())


def test_unknown_atlas_user_rejected(linker):
    code = linker.request_code(TelegramUser("100", "200"))
    with pytest.raises(TelegramLinkError) as caught:
        linker.confirm_code(code, "Unknown", user_exists=lambda _: False)
    assert caught.value.code == "atlas_user_not_found"


def test_cancel_invalidates_pending_code(linker):
    code = linker.request_code(TelegramUser("100", "200"))
    assert linker.cancel_pending("100", "200") is True
    with pytest.raises(TelegramLinkError):
        linker.confirm_code(code, "Liam", user_exists=lambda _: True)


def test_unlink_keeps_atlas_identity_but_removes_association(linker):
    code = linker.request_code(TelegramUser("100", "200"))
    linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    assert linker.unlink("100", "200") is True
    account = linker.get_account("100")
    assert account["atlas_user_id"] is None
    assert "chat_id" not in account
    assert "username" not in account


def test_revoke_by_atlas_user(linker):
    code = linker.request_code(TelegramUser("100", "200"))
    linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    assert linker.revoke(atlas_user_id="Liam") is True
    assert linker.get_account("100")["state"] == "revoked"


def test_used_proposal_keeps_no_code_or_telegram_metadata(linker, storage):
    code = linker.request_code(TelegramUser("100", "200"))
    linker.confirm_code(code, "Liam", user_exists=lambda _: True)
    proposal = next(iter(storage.section("link_codes").values()))
    assert proposal["state"] == "used"
    assert set(proposal) == {"state", "closed_at"}


def test_same_username_does_not_merge_accounts(linker):
    first = linker.request_code(TelegramUser("100", "200", username="same"))
    second = linker.request_code(TelegramUser("101", "201", username="same"))
    linker.confirm_code(first, "Liam", user_exists=lambda _: True)
    linker.confirm_code(second, "Saray", user_exists=lambda _: True)
    assert linker.get_account("100")["atlas_user_id"] == "Liam"
    assert linker.get_account("101")["atlas_user_id"] == "Saray"
