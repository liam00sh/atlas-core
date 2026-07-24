"""Construcción configurable del entorno de Home Assistant de la Etapa E."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automation.automation_manager import AutomationManager
from automation.automation_permissions import AutomationPermissions, UserAccess
from automation.automation_registry import AutomationRegistry
from automation.home_assistant_adapter import HomeAssistantAdapter
from automation.home_assistant_client import BaseHomeAssistantClient
from automation.home_assistant_factory import (
    create_home_assistant_client,
    load_home_assistant_settings,
)
from automation.home_assistant_models import (
    HomeEntityDefinition,
    HomeEntityKind,
    HomeEntityMode,
    HomeEntityRisk,
    HomeEntityState,
)
from automation.home_assistant_simulator import HomeAssistantSimulator
from automation.home_device_registry import HomeDeviceRegistry
from automation.stage_e_catalog import build_stage_e_actions


@dataclass(slots=True)
class StageEEnvironment:
    manager: AutomationManager
    action_registry: AutomationRegistry
    device_registry: HomeDeviceRegistry
    adapter: HomeAssistantAdapter
    client: BaseHomeAssistantClient
    simulator: HomeAssistantSimulator | None
    household_user_ids: frozenset[str]
    guest_user_ids: frozenset[str]
    present_guest_user_ids: set[str]

    @staticmethod
    def normalize_user_id(user_id: str) -> str:
        return str(user_id).strip().casefold()

    def is_guest(self, user_id: str) -> bool:
        return self.normalize_user_id(user_id) in self.guest_user_ids

    def is_guest_present(self, user_id: str) -> bool:
        return self.normalize_user_id(user_id) in self.present_guest_user_ids

    def set_guest_presence(self, user_id: str, present: bool) -> None:
        normalized = self.normalize_user_id(user_id)
        if normalized not in self.guest_user_ids:
            raise ValueError("El usuario no está registrado como invitado de esta casa.")
        if present:
            self.present_guest_user_ids.add(normalized)
        else:
            self.present_guest_user_ids.discard(normalized)


def _simulated_entities() -> tuple[list[HomeEntityDefinition], dict[str, HomeEntityState]]:
    entities = [
        HomeEntityDefinition(
            entity_id="light.atlas_virtual",
            name="Luz virtual Atlas",
            kind=HomeEntityKind.LIGHT,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.LOW,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.light",
        ),
        HomeEntityDefinition(
            entity_id="switch.atlas_virtual",
            name="Enchufe virtual Atlas",
            kind=HomeEntityKind.SWITCH,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.MEDIUM,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.switch",
        ),
        HomeEntityDefinition(
            entity_id="sensor.atlas_temperature",
            name="Temperatura simulada Atlas",
            kind=HomeEntityKind.SENSOR,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.READ_ONLY,
            allowed_services=frozenset(),
            required_permission="home.read",
        ),
    ]
    states = {
        "light.atlas_virtual": HomeEntityState("light.atlas_virtual", "off", {"friendly_name": "Luz virtual Atlas"}),
        "switch.atlas_virtual": HomeEntityState("switch.atlas_virtual", "off", {"friendly_name": "Enchufe virtual Atlas"}),
        "sensor.atlas_temperature": HomeEntityState(
            "sensor.atlas_temperature",
            "22.5",
            {"friendly_name": "Temperatura simulada Atlas", "unit_of_measurement": "°C"},
        ),
    }
    return entities, states


def _real_lab_entities() -> list[HomeEntityDefinition]:
    """
    Catálogo cerrado del laboratorio virtual y de los enchufes reales.

    Home Assistant no expone un interruptor maestro independiente para el
    alargador doble. "Apagar el acuario pequeño" se resuelve como una acción
    agrupada sobre Luz + Oxígeno.
    """

    return [
        HomeEntityDefinition(
            entity_id="switch.salon_acuario_grande_luz_acuario_grande",
            name="Luz del acuario grande",
            kind=HomeEntityKind.SWITCH,
            mode=HomeEntityMode.PHYSICAL,
            risk=HomeEntityRisk.MEDIUM,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.switch",
            metadata={"area": "salon", "group": "acuario_grande"},
        ),
        HomeEntityDefinition(
            entity_id="switch.despacho_acuario_pequeno_luz_acuario_pequeno",
            name="Luz del acuario pequeño",
            kind=HomeEntityKind.SWITCH,
            mode=HomeEntityMode.PHYSICAL,
            risk=HomeEntityRisk.MEDIUM,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.switch",
            metadata={"area": "despacho", "group": "acuario_pequeno"},
        ),
        HomeEntityDefinition(
            entity_id="switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno",
            name="Oxígeno del acuario pequeño",
            kind=HomeEntityKind.SWITCH,
            mode=HomeEntityMode.PHYSICAL,
            risk=HomeEntityRisk.MEDIUM,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.switch",
            metadata={"area": "despacho", "group": "acuario_pequeno"},
        ),
        HomeEntityDefinition(
            entity_id="light.atlas_light_lab",
            name="Luz de laboratorio Atlas",
            kind=HomeEntityKind.LIGHT,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.LOW,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.light",
        ),
        HomeEntityDefinition(
            entity_id="switch.atlas_plug_lab",
            name="Enchufe de laboratorio Atlas",
            kind=HomeEntityKind.SWITCH,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.MEDIUM,
            allowed_services=frozenset({"turn_on", "turn_off"}),
            required_permission="home.control.switch",
        ),
        HomeEntityDefinition(
            entity_id="sensor.atlas_temperature_lab",
            name="Temperatura de laboratorio Atlas",
            kind=HomeEntityKind.SENSOR,
            mode=HomeEntityMode.VIRTUAL,
            risk=HomeEntityRisk.READ_ONLY,
            allowed_services=frozenset(),
            required_permission="home.read",
        ),
    ]


def _build_environment(
    storage_path: str | Path,
    *,
    client: BaseHomeAssistantClient,
    entities: list[HomeEntityDefinition],
    owner_user_id: str,
    household_user_ids: tuple[str, ...],
    guest_user_ids: tuple[str, ...],
    present_guest_user_ids: tuple[str, ...],
) -> StageEEnvironment:
    device_registry = HomeDeviceRegistry()
    device_registry.register_many(entities)
    adapter = HomeAssistantAdapter(client, device_registry)

    action_registry = AutomationRegistry()
    action_registry.register_many(build_stage_e_actions(adapter))
    permissions = AutomationPermissions()

    normalized_owner = str(owner_user_id).strip().casefold()
    normalized_household = {str(x).strip().casefold() for x in household_user_ids if str(x).strip()}
    normalized_household.add(normalized_owner)
    normalized_guests = {str(x).strip().casefold() for x in guest_user_ids if str(x).strip()}
    normalized_present = {
        str(x).strip().casefold() for x in present_guest_user_ids if str(x).strip()
    }.intersection(normalized_guests)

    for user_id in sorted(normalized_household):
        permissions.set_user(UserAccess(
            user_id=user_id,
            roles={"owner"} if user_id == normalized_owner else {"household"},
            groups={"current_household"},
            permissions={"home.read", "home.control.light", "home.control.switch"},
        ))
    for user_id in sorted(normalized_guests):
        permissions.set_user(UserAccess(
            user_id=user_id,
            roles={"guest"},
            groups={"current_house_guests"},
            permissions={"home.read", "home.control.light", "home.control.switch"} if user_id in normalized_present else set(),
        ))

    manager = AutomationManager(storage_path=storage_path, registry=action_registry, permissions=permissions)
    simulator = client if isinstance(client, HomeAssistantSimulator) else None
    return StageEEnvironment(
        manager=manager,
        action_registry=action_registry,
        device_registry=device_registry,
        adapter=adapter,
        client=client,
        simulator=simulator,
        household_user_ids=frozenset(normalized_household),
        guest_user_ids=frozenset(normalized_guests),
        present_guest_user_ids=set(normalized_present),
    )


def build_stage_e_simulation(
    storage_path: str | Path,
    *,
    owner_user_id: str = "REDACTED_f73137d930c3",
    household_user_ids: tuple[str, ...] = (
        "REDACTED_f73137d930c3",
        "maria REDACTED_1ec4ed037766",
        "REDACTED_1ec4ed037766 vicente navarro",
        "REDACTED_1552db05a755",
        "REDACTED_72534c4a93dd",
    ),
    guest_user_ids: tuple[str, ...] = ("REDACTED_7b9528898599", "raul"),
    present_guest_user_ids: tuple[str, ...] = (),
) -> StageEEnvironment:
    entities, states = _simulated_entities()
    client = HomeAssistantSimulator(states)
    return _build_environment(
        storage_path,
        client=client,
        entities=entities,
        owner_user_id=owner_user_id,
        household_user_ids=household_user_ids,
        guest_user_ids=guest_user_ids,
        present_guest_user_ids=present_guest_user_ids,
    )


def build_stage_e_environment(
    storage_path: str | Path,
    *,
    env_file: str | Path | None = None,
    environ: dict[str, str] | None = None,
    owner_user_id: str = "REDACTED_f73137d930c3",
    household_user_ids: tuple[str, ...] = (
        "REDACTED_f73137d930c3",
        "maria REDACTED_1ec4ed037766",
        "REDACTED_1ec4ed037766 vicente navarro",
        "REDACTED_1552db05a755",
        "REDACTED_72534c4a93dd",
    ),
    guest_user_ids: tuple[str, ...] = ("REDACTED_7b9528898599", "raul"),
    present_guest_user_ids: tuple[str, ...] = (),
) -> StageEEnvironment:
    settings = load_home_assistant_settings(environ, env_file=env_file)
    if settings.mode == "simulated":
        entities, states = _simulated_entities()
        client = create_home_assistant_client(settings, initial_states=states)
    else:
        entities = _real_lab_entities()
        client = create_home_assistant_client(settings)
    return _build_environment(
        storage_path,
        client=client,
        entities=entities,
        owner_user_id=owner_user_id,
        household_user_ids=household_user_ids,
        guest_user_ids=guest_user_ids,
        present_guest_user_ids=present_guest_user_ids,
    )
