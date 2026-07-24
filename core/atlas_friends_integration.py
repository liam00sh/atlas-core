from config import DATA_DIR
from core.atlas_friends import FriendsRepository, FriendshipLevel


class AtlasFriendsMixin:
    def _init_friends(self) -> None:
        self.friends_repository = FriendsRepository(DATA_DIR / "people_relationships.json")

    def remember_known_person(
        self,
        *,
        display_name: str,
        told_by: str,
        relation_owner: str | None = None,
        friendship_level: int = 0,
    ):
        try:
            level = FriendshipLevel(friendship_level)
        except ValueError as exc:
            raise ValueError("El nivel de amistad debe estar entre 0 y 4.") from exc
        person = self.friends_repository.upsert_person(display_name)
        if relation_owner is not None:
            owner = self.friends_repository.upsert_person(relation_owner)
            self.friends_repository.set_relation_level(
                owner_person_id=owner.person_id,
                target_person_id=person.person_id,
                new_level=level,
                confidence=1.0,
                source=f"presentación de {told_by}",
                automatic=False,
                confirmed_by_user=True,
            )
        return person

    def remember_person_fact(
        self,
        *,
        person_name: str,
        fact_type: str,
        value,
        told_by: str,
        visibility: str = "related_profiles",
        sensitivity: str = "normal",
        confidence: float = 1.0,
        source: str = "conversation",
    ) -> None:
        person = self.friends_repository.find_person(person_name) or self.friends_repository.upsert_person(person_name)
        self.friends_repository.save_fact(
            person_id=person.person_id,
            fact_type=fact_type,
            value=value,
            told_by=told_by,
            visibility=visibility,
            sensitivity=sensitivity,
            confidence=confidence,
            source=source,
        )
