"""Vinculacion segura entre una cuenta Telegram y un usuario Atlas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Any, Callable

from telegram_interface.models import TelegramAccountState, TelegramUser
from telegram_interface.storage import TelegramStorage, utc_now_text


LINK_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_LINK_ATTEMPTS = 5


class TelegramLinkError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class TelegramIdentityLinker:
    def __init__(self, storage: TelegramStorage, *, ttl_seconds: int = 600) -> None:
        self.storage = storage
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _derive(code: str, salt_hex: str) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256", code.strip().upper().encode("utf-8"), bytes.fromhex(salt_hex), 120_000
        )
        return digest.hex()

    def get_account(self, telegram_user_id: object) -> dict[str, Any]:
        account = self.storage.section("accounts").get(str(telegram_user_id))
        if not isinstance(account, dict):
            return {"state": TelegramAccountState.UNLINKED.value, "atlas_user_id": None}
        return account

    @staticmethod
    def _minimize_proposal(proposal: dict[str, Any], state: str) -> None:
        proposal.clear()
        proposal.update({"state": state, "closed_at": utc_now_text()})

    def request_code(self, user: TelegramUser) -> str:
        now = datetime.now(UTC)
        # A code cannot be reconstructed from its hash. Returning an existing
        # code would require storing plaintext, so a repeated /start cancels
        # the prior proposal and creates a fresh one.
        code_prefix = "".join(secrets.choice(LINK_ALPHABET) for _ in range(3))
        code = code_prefix + "".join(secrets.choice(LINK_ALPHABET) for _ in range(7))
        salt = secrets.token_bytes(16).hex()
        code_hash = self._derive(code, salt)
        code_id = secrets.token_hex(12)

        def mutate(data: dict[str, Any]) -> None:
            for proposal in data["link_codes"].values():
                if (
                    proposal.get("telegram_user_id") == user.telegram_user_id
                    and proposal.get("state") == "pending"
                ):
                    self._minimize_proposal(proposal, "cancelled")
            data["link_codes"][code_id] = {
                "code_hash": code_hash,
                "code_prefix": code_prefix,
                "salt": salt,
                "telegram_user_id": user.telegram_user_id,
                "chat_id": user.chat_id,
                "expires_at": (now + timedelta(seconds=self.ttl_seconds)).isoformat(),
                "attempts_left": MAX_LINK_ATTEMPTS,
                "state": "pending",
                "created_at": now.isoformat(),
            }
            previous = data["accounts"].get(user.telegram_user_id, {})
            if previous.get("state") not in {"linked", "blocked", "revoked"}:
                data["accounts"][user.telegram_user_id] = {
                    "state": TelegramAccountState.LINK_PENDING.value,
                    "atlas_user_id": None,
                    "chat_id": user.chat_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "updated_at": utc_now_text(),
                }
        self.storage.update(mutate)
        return code

    def confirm_code(
        self,
        code: str,
        atlas_user_id: str,
        *,
        user_exists: Callable[[str], bool],
    ) -> dict[str, Any]:
        clean_user = atlas_user_id.strip()
        if not clean_user or not user_exists(clean_user):
            raise TelegramLinkError("El usuario Atlas de destino no existe.", "atlas_user_not_found")
        now = datetime.now(UTC)

        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            selected: tuple[str, dict[str, Any]] | None = None
            for code_id, proposal in data["link_codes"].items():
                if proposal.get("state") != "pending":
                    continue
                if proposal.get("code_prefix") != code.strip().upper()[:3]:
                    continue
                try:
                    expected = self._derive(code, str(proposal.get("salt", "")))
                except ValueError:
                    self._minimize_proposal(proposal, "invalid")
                    continue
                if hmac.compare_digest(expected, str(proposal.get("code_hash", ""))):
                    selected = (code_id, proposal)
                    break
            if selected is None:
                # Reduce the remaining attempts for pending proposals without
                # revealing which Telegram account owns a code.
                prefix = code.strip().upper()[:3]
                for proposal in data["link_codes"].values():
                    if proposal.get("state") == "pending" and proposal.get("code_prefix") == prefix:
                        proposal["attempts_left"] = max(0, int(proposal.get("attempts_left", 0)) - 1)
                        if proposal["attempts_left"] == 0:
                            account = data["accounts"].get(str(proposal.get("telegram_user_id")))
                            if account and account.get("state") == "link_pending":
                                account["state"] = "blocked"
                            self._minimize_proposal(proposal, "blocked")
                return {"error": "invalid_link_code"}
            code_id, proposal = selected
            if datetime.fromisoformat(proposal["expires_at"]) <= now:
                account = data["accounts"].get(str(proposal.get("telegram_user_id")))
                if account and account.get("state") == "link_pending":
                    account["state"] = "unlinked"
                self._minimize_proposal(proposal, "expired")
                return {"error": "expired_link_code"}
            telegram_user_id = str(proposal["telegram_user_id"])
            chat_id = proposal["chat_id"]
            self._minimize_proposal(proposal, "used")
            account = data["accounts"].setdefault(telegram_user_id, {})
            account.update({
                "state": TelegramAccountState.LINKED.value,
                "atlas_user_id": clean_user,
                "chat_id": chat_id,
                "linked_at": now.isoformat(),
                "updated_at": now.isoformat(),
            })
            return {"telegram_user_id": telegram_user_id, "atlas_user_id": clean_user, "code_id": code_id}
        result = self.storage.update(mutate)
        if result.get("error") == "invalid_link_code":
            raise TelegramLinkError("El codigo no es valido.", "invalid_link_code")
        if result.get("error") == "expired_link_code":
            raise TelegramLinkError("El codigo ha caducado.", "expired_link_code")
        return result

    def cancel_pending(self, telegram_user_id: object, chat_id: object) -> bool:
        def mutate(data: dict[str, Any]) -> bool:
            changed = False
            for proposal in data["link_codes"].values():
                if (
                    proposal.get("telegram_user_id") == str(telegram_user_id)
                    and proposal.get("chat_id") == str(chat_id)
                    and proposal.get("state") == "pending"
                ):
                    self._minimize_proposal(proposal, "cancelled")
                    changed = True
            account = data["accounts"].get(str(telegram_user_id))
            if account and account.get("state") == "link_pending":
                account["state"] = "unlinked"
                for field in ("chat_id", "username", "first_name", "last_name"):
                    account.pop(field, None)
            return changed
        return self.storage.update(mutate)

    def unlink(self, telegram_user_id: object, chat_id: object) -> bool:
        def mutate(data: dict[str, Any]) -> bool:
            account = data["accounts"].get(str(telegram_user_id))
            if not account or account.get("chat_id") != str(chat_id) or account.get("state") != "linked":
                return False
            account.update({"state": "unlinked", "atlas_user_id": None, "updated_at": utc_now_text()})
            for field in ("chat_id", "username", "first_name", "last_name", "linked_at"):
                account.pop(field, None)
            for key in list(data["sessions"]):
                if key.startswith(f"{telegram_user_id}:"):
                    del data["sessions"][key]
            return True
        return self.storage.update(mutate)

    def revoke(self, *, telegram_user_id: str | None = None, atlas_user_id: str | None = None) -> bool:
        def mutate(data: dict[str, Any]) -> bool:
            changed = False
            for account_id, account in data["accounts"].items():
                matches = telegram_user_id is not None and account_id == str(telegram_user_id)
                matches = matches or (
                    atlas_user_id is not None
                    and str(account.get("atlas_user_id", "")).casefold() == atlas_user_id.casefold()
                )
                if matches:
                    account.update({"state": "revoked", "atlas_user_id": None, "updated_at": utc_now_text()})
                    for field in ("chat_id", "username", "first_name", "last_name", "linked_at"):
                        account.pop(field, None)
                    changed = True
            return changed
        return self.storage.update(mutate)
