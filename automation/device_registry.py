"""
Proyecto Atlas
Archivo: automation/device_registry.py

Registro en memoria de dispositivos. La persistencia se añadirá después de
validar el modelo en la Etapa D.
"""

from __future__ import annotations

from automation.device_models import DeviceRecord, TrustLevel


class DeviceRegistryError(RuntimeError):
    """Error controlado del registro de dispositivos."""


class DeviceRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, DeviceRecord] = {}

    def register(self, device: DeviceRecord) -> None:
        if not device.device_id.strip():
            raise ValueError("device_id no puede estar vacío.")
        if device.device_id in self._devices:
            raise DeviceRegistryError(
                f"El dispositivo {device.device_id!r} ya está registrado."
            )
        self._devices[device.device_id] = device

    def replace(self, device: DeviceRecord) -> None:
        if device.device_id not in self._devices:
            raise DeviceRegistryError(
                f"El dispositivo {device.device_id!r} no existe."
            )
        self._devices[device.device_id] = device

    def get(self, device_id: str) -> DeviceRecord:
        try:
            return self._devices[device_id]
        except KeyError as exc:
            raise DeviceRegistryError(
                f"El dispositivo {device_id!r} no está registrado."
            ) from exc

    def list_all(self) -> tuple[DeviceRecord, ...]:
        return tuple(
            self._devices[key]
            for key in sorted(self._devices)
        )

    def list_for_owner(self, owner_user_id: str) -> tuple[DeviceRecord, ...]:
        return tuple(
            device
            for device in self.list_all()
            if device.owner_user_id == owner_user_id
        )

    def revoke(self, device_id: str, reason: str) -> DeviceRecord:
        current = self.get(device_id)
        revoked = DeviceRecord(
            device_id=current.device_id,
            display_name=current.display_name,
            owner_user_id=current.owner_user_id,
            device_type=current.device_type,
            operating_system=current.operating_system,
            agent_name=current.agent_name,
            agent_version=current.agent_version,
            trust_level=TrustLevel.REVOKED,
            capabilities=current.capabilities,
            shared_capabilities=current.shared_capabilities,
            online=False,
            requires_local_presence=current.requires_local_presence,
            confirmation_methods=current.confirmation_methods,
            created_at=current.created_at,
            last_seen_at=current.last_seen_at,
            revoked_reason=reason.strip() or "Sin motivo indicado.",
        )
        self._devices[device_id] = revoked
        return revoked
