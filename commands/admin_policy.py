"""Política central para comandos administrativos de Atlas."""

from __future__ import annotations

from core import context

ADMIN_USER_ID = "REDACTED_f73137d930c3"


def current_user_id() -> str:
    atlas = getattr(context, "atlas", None)
    if atlas is None:
        return ""

    for attribute in ("current_user_id", "active_user_id"):
        value = getattr(atlas, attribute, None)
        if value:
            return str(value).strip().casefold()

    current_user = getattr(atlas, "current_user", None)
    if current_user is not None:
        if isinstance(current_user, str):
            return current_user.strip().casefold()
        for attribute in ("user_id", "id", "name"):
            value = getattr(current_user, attribute, None)
            if value:
                return str(value).strip().casefold()

    user_manager = getattr(atlas, "users", None) or getattr(atlas, "user_manager", None)
    if user_manager is not None:
        for attribute in ("current_user_id", "active_user_id"):
            value = getattr(user_manager, attribute, None)
            if value:
                return str(value).strip().casefold()
        current = getattr(user_manager, "current_user", None)
        if current is not None:
            if isinstance(current, str):
                return current.strip().casefold()
            for attribute in ("user_id", "id", "name"):
                value = getattr(current, attribute, None)
                if value:
                    return str(value).strip().casefold()

    return ""


def is_admin_user() -> bool:
    return current_user_id() == ADMIN_USER_ID


def require_admin_user() -> bool:
    if is_admin_user():
        return True

    print()
    print("Esta es una función administrativa esencial de Atlas.")
    print("Solo REDACTED_2c7b6821719d puede utilizarla.")
    return False
