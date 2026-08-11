"""Política de presencia para el acceso familiar al PC de Alex."""

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


def can_access_Alex_pc(
    *,
    user_id: str,
    presence: PresenceStatus = PresenceStatus.UNKNOWN,
) -> PcAccessDecision:
    normalized = str(user_id).strip().casefold()

    if normalized == "alex":
        return PcAccessDecision(True, "administrator_owner")

    if normalized != "vega":
        return PcAccessDecision(False, "user_not_authorized")

    if presence == PresenceStatus.HOME_VERIFIED:
        return PcAccessDecision(True, "home_presence_verified")

    if presence == PresenceStatus.AWAY_VERIFIED:
        return PcAccessDecision(False, "user_away_from_home")

    return PcAccessDecision(False, "home_presence_not_verified")
