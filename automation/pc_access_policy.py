"""Política de presencia para el acceso familiar al PC de REDACTED_2c7b6821719d."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PresenceStatus(StrEnum):
    HOME_VERIFIED = "home_verified"
    AWAY_VERIFIED = "away_verified"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PcAccessDecision:
    allowed: bool
    reason: str


def can_access_REDACTED_f73137d930c3_pc(
    *,
    user_id: str,
    presence: PresenceStatus = PresenceStatus.UNKNOWN,
) -> PcAccessDecision:
    normalized = str(user_id).strip().casefold()

    if normalized == "REDACTED_f73137d930c3":
        return PcAccessDecision(True, "administrator_owner")

    if normalized != "REDACTED_7b9528898599":
        return PcAccessDecision(False, "user_not_authorized")

    if presence == PresenceStatus.HOME_VERIFIED:
        return PcAccessDecision(True, "home_presence_verified")

    if presence == PresenceStatus.AWAY_VERIFIED:
        return PcAccessDecision(False, "user_away_from_home")

    return PcAccessDecision(False, "home_presence_not_verified")
