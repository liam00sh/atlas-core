from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import IntEnum
import json
from pathlib import Path
from typing import Any, Iterable


class FriendshipLevel(IntEnum):
    KNOWN = 0
    KNOWN_FRIEND = 1
    FRIEND = 2
    CLOSE_FRIEND = 3
    BEST_FRIEND = 4


FRIENDSHIP_LEVEL_NAMES = {
    FriendshipLevel.KNOWN: "conocido",
    FriendshipLevel.KNOWN_FRIEND: "amigo conocido",
    FriendshipLevel.FRIEND: "amigo",
    FriendshipLevel.CLOSE_FRIEND: "amigo cercano",
    FriendshipLevel.BEST_FRIEND: "mejor amigo",
}

VISIBLE_RELATION_LABEL = {
    FriendshipLevel.KNOWN: "conocido",
    FriendshipLevel.KNOWN_FRIEND: "amigo",
    FriendshipLevel.FRIEND: "amigo",
    FriendshipLevel.CLOSE_FRIEND: "amigo",
    FriendshipLevel.BEST_FRIEND: "amigo",
}

MIN_DELEGABLE_FRIENDSHIP_LEVEL = FriendshipLevel.CLOSE_FRIEND
AUTO_APPLY_CONFIDENCE = 0.85
ASK_USER_CONFIDENCE = 0.60


@dataclass(slots=True)
class RelationshipHistoryEntry:
    changed_at: str
    old_level: int
    new_level: int
    confidence: float
    source: str
    automatic: bool
    confirmed_by_user: bool
    note: str | None = None


@dataclass(slots=True)
class FriendshipRelation:
    owner_person_id: str
    target_person_id: str
    level: int = int(FriendshipLevel.KNOWN)
    confidence: float = 1.0
    is_family: bool = False
    romantic_status: str | None = None
    active: bool = True
    updated_at: str = ""
    history: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if not self.updated_at:
            self.updated_at = _utc_now()
        if self.history is None:
            self.history = []

    @property
    def friendship_level(self) -> FriendshipLevel:
        return FriendshipLevel(self.level)

    @property
    def visible_label(self) -> str:
        return VISIBLE_RELATION_LABEL[self.friendship_level]


@dataclass(slots=True)
class KnownPerson:
    person_id: str
    display_name: str
    aliases: list[str]
    profile_id: str | None = None
    facts: list[dict[str, Any]] | None = None
    relationships: list[dict[str, Any]] | None = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = _utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if self.facts is None:
            self.facts = []
        if self.relationships is None:
            self.relationships = []


@dataclass(slots=True)
class PermissionGrant:
    grantor_profile_id: str
    target_person_id: str
    permission: str
    scope: str | None
    created_at: str
    expires_at: str | None = None
    requires_home_presence: bool = True
    active: bool = True


@dataclass(slots=True)
class RelationshipChangeDecision:
    action: str
    current_level: int
    proposed_level: int
    confidence: float
    message: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_person_id(name: str) -> str:
    value = " ".join(name.casefold().strip().split())
    safe = "".join(ch if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in safe.split("_") if part)


class FriendsRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            from config import DATA_DIR
            path = DATA_DIR / "people_relationships.json"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"people": {}, "relations": {}, "permission_grants": [], "pending_relationship_changes": []})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"people": {}, "relations": {}, "permission_grants": [], "pending_relationship_changes": []}

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def upsert_person(
        self,
        display_name: str,
        *,
        aliases: Iterable[str] = (),
        profile_id: str | None = None,
    ) -> KnownPerson:
        display_name = " ".join(str(display_name).strip().split())
        if not display_name:
            raise ValueError("El nombre visible de la persona no puede estar vacío.")
        data = self._read()
        person_id = normalize_person_id(display_name)
        raw = data["people"].get(person_id)
        if raw:
            person = KnownPerson(**raw)
            person.display_name = display_name
            person.aliases = sorted(set(person.aliases) | set(aliases))
            if profile_id:
                person.profile_id = profile_id
            person.updated_at = _utc_now()
        else:
            person = KnownPerson(
                person_id=person_id,
                display_name=display_name,
                aliases=sorted(set(aliases)),
                profile_id=profile_id,
            )
        data["people"][person_id] = asdict(person)
        self._write(data)
        return person

    def find_person(self, name_or_id: str) -> KnownPerson | None:
        data = self._read()
        person_id = normalize_person_id(name_or_id)
        raw = data["people"].get(person_id)
        if raw:
            return KnownPerson(**raw)
        lowered = name_or_id.casefold().strip()
        for item in data["people"].values():
            names = [item.get("display_name", ""), *item.get("aliases", [])]
            if any(lowered == str(name).casefold().strip() for name in names):
                return KnownPerson(**item)
        return None

    def link_profile(self, person_id: str, profile_id: str) -> None:
        data = self._read()
        person = data["people"].get(person_id)
        if person is None:
            raise KeyError(f"Persona no encontrada: {person_id}")
        person["profile_id"] = profile_id
        person["updated_at"] = _utc_now()
        self._write(data)

    def save_fact(
        self,
        *,
        person_id: str,
        fact_type: str,
        value: Any,
        told_by: str,
        visibility: str,
        sensitivity: str,
        confidence: float,
        source: str,
    ) -> None:
        data = self._read()
        person = data["people"].get(person_id)
        if person is None:
            raise KeyError(f"Persona no encontrada: {person_id}")
        person.setdefault("facts", []).append(
            {
                "fact_type": fact_type,
                "value": value,
                "told_by": told_by,
                "visibility": visibility,
                "sensitivity": sensitivity,
                "confidence": confidence,
                "source": source,
                "created_at": _utc_now(),
            }
        )
        person["updated_at"] = _utc_now()
        self._write(data)

    def _relation_key(self, owner_person_id: str, target_person_id: str) -> str:
        return f"{owner_person_id}::{target_person_id}"

    def get_relation(self, owner_person_id: str, target_person_id: str) -> FriendshipRelation | None:
        data = self._read()
        raw = data["relations"].get(self._relation_key(owner_person_id, target_person_id))
        return FriendshipRelation(**raw) if raw else None

    def set_relation_level(
        self,
        *,
        owner_person_id: str,
        target_person_id: str,
        new_level: FriendshipLevel,
        confidence: float,
        source: str,
        automatic: bool,
        confirmed_by_user: bool,
        note: str | None = None,
    ) -> FriendshipRelation:
        data = self._read()
        key = self._relation_key(owner_person_id, target_person_id)
        raw = data["relations"].get(key)
        relation = FriendshipRelation(**raw) if raw else FriendshipRelation(
            owner_person_id=owner_person_id,
            target_person_id=target_person_id,
        )
        old_level = relation.level
        new_level = FriendshipLevel(new_level)
        if owner_person_id == target_person_id:
            raise ValueError("Una persona no puede tener una relación de amistad consigo misma.")
        if owner_person_id not in data.get("people", {}) or target_person_id not in data.get("people", {}):
            raise KeyError("Ambas personas deben existir antes de registrar la relación.")
        relation.level = int(new_level)
        relation.confidence = float(confidence)
        relation.updated_at = _utc_now()
        relation.history.append(asdict(RelationshipHistoryEntry(
            changed_at=relation.updated_at,
            old_level=old_level,
            new_level=int(new_level),
            confidence=float(confidence),
            source=source,
            automatic=automatic,
            confirmed_by_user=confirmed_by_user,
            note=note,
        )))
        data["relations"][key] = asdict(relation)
        self._write(data)
        return relation

    def propose_or_apply_level_change(
        self,
        *,
        owner_person_id: str,
        target_person_id: str,
        proposed_level: FriendshipLevel,
        confidence: float,
        source: str,
        note: str | None = None,
    ) -> RelationshipChangeDecision:
        current = self.get_relation(owner_person_id, target_person_id)
        current_level = int(current.friendship_level if current else FriendshipLevel.KNOWN)

        if confidence >= AUTO_APPLY_CONFIDENCE:
            self.set_relation_level(
                owner_person_id=owner_person_id,
                target_person_id=target_person_id,
                new_level=proposed_level,
                confidence=confidence,
                source=source,
                automatic=True,
                confirmed_by_user=False,
                note=note,
            )
            return RelationshipChangeDecision(
                action="applied",
                current_level=current_level,
                proposed_level=int(proposed_level),
                confidence=confidence,
                message="Cambio aplicado automáticamente por alta confianza.",
            )

        if confidence >= ASK_USER_CONFIDENCE:
            self._save_pending_change(
                owner_person_id=owner_person_id,
                target_person_id=target_person_id,
                proposed_level=proposed_level,
                confidence=confidence,
                source=source,
                note=note,
            )
            return RelationshipChangeDecision(
                action="ask",
                current_level=current_level,
                proposed_level=int(proposed_level),
                confidence=confidence,
                message="Atlas debe pedir confirmación antes de cambiar la relación.",
            )

        return RelationshipChangeDecision(
            action="keep",
            current_level=current_level,
            proposed_level=int(proposed_level),
            confidence=confidence,
            message="Confianza insuficiente; se conserva la relación actual.",
        )

    def _save_pending_change(
        self,
        *,
        owner_person_id: str,
        target_person_id: str,
        proposed_level: FriendshipLevel,
        confidence: float,
        source: str,
        note: str | None,
    ) -> None:
        data = self._read()
        pending = data.setdefault("pending_relationship_changes", [])
        pending[:] = [
            item for item in pending
            if not (
                item.get("owner_person_id") == owner_person_id
                and item.get("target_person_id") == target_person_id
            )
        ]
        pending.append({
            "owner_person_id": owner_person_id,
            "target_person_id": target_person_id,
            "proposed_level": int(proposed_level),
            "confidence": float(confidence),
            "source": source,
            "note": note,
            "created_at": _utc_now(),
        })
        self._write(data)

    def confirm_pending_relationship_change(
        self,
        *,
        owner_person_id: str,
        target_person_id: str,
        accept: bool,
    ) -> FriendshipRelation | None:
        data = self._read()
        pending = data.setdefault("pending_relationship_changes", [])
        match = None
        remaining = []
        for item in pending:
            if item["owner_person_id"] == owner_person_id and item["target_person_id"] == target_person_id and match is None:
                match = item
            else:
                remaining.append(item)
        data["pending_relationship_changes"] = remaining
        self._write(data)
        if match is None or not accept:
            return None
        return self.set_relation_level(
            owner_person_id=owner_person_id,
            target_person_id=target_person_id,
            new_level=FriendshipLevel(match["proposed_level"]),
            confidence=float(match["confidence"]),
            source=match["source"],
            automatic=False,
            confirmed_by_user=True,
            note=match.get("note"),
        )

    def grant_permission(
        self,
        *,
        grantor_profile_id: str,
        target_person_id: str,
        permission: str,
        scope: str | None,
        grantor_permissions: set[str],
        delegable_permissions: set[str],
        friendship_level: FriendshipLevel,
        target_is_home: bool,
        is_admin_permission: bool,
        grantor_is_admin: bool,
    ) -> PermissionGrant:
        friendship_level = FriendshipLevel(friendship_level)
        if not permission or not str(permission).strip():
            raise ValueError("El permiso no puede estar vacío.")
        if scope is None or not str(scope).strip():
            raise PermissionError("Todo permiso delegado debe tener un alcance concreto.")
        if is_admin_permission:
            raise PermissionError("Los permisos administrativos no se delegan.")
        if friendship_level < MIN_DELEGABLE_FRIENDSHIP_LEVEL:
            raise PermissionError("Solo amistades de nivel 3 o 4 pueden recibir permisos.")
        if permission not in grantor_permissions and not grantor_is_admin:
            raise PermissionError("El concedente no posee ese permiso.")
        if permission not in delegable_permissions:
            raise PermissionError("El permiso no es delegable.")
        if not target_is_home:
            raise PermissionError("El permiso solo puede utilizarse cuando la persona está en casa.")

        grant = PermissionGrant(
            grantor_profile_id=grantor_profile_id,
            target_person_id=target_person_id,
            permission=permission,
            scope=scope,
            created_at=_utc_now(),
            requires_home_presence=True,
        )
        data = self._read()
        data.setdefault("permission_grants", []).append(asdict(grant))
        self._write(data)
        return grant

    def permission_is_effective(self, grant: PermissionGrant, *, target_is_home: bool) -> bool:
        if not grant.active:
            return False
        if grant.expires_at:
            try:
                expires_at = datetime.fromisoformat(grant.expires_at)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= expires_at:
                    return False
            except ValueError:
                return False
        if grant.requires_home_presence and not target_is_home:
            return False
        return True


    def has_effective_permission(
        self,
        *,
        target_person_id: str,
        permission: str,
        target_is_home: bool,
    ) -> bool:
        data = self._read()
        for raw in data.get("permission_grants", []):
            if raw.get("target_person_id") == target_person_id and raw.get("permission") == permission:
                grant = PermissionGrant(**raw)
                if self.permission_is_effective(grant, target_is_home=target_is_home):
                    return True
        return False


def user_visible_relation(relation: FriendshipRelation) -> str:
    if relation.romantic_status:
        if relation.visible_label == "amigo":
            return f"{relation.romantic_status} y amigo"
        return relation.romantic_status
    return relation.visible_label
