from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

"""
Prueba manual de la simulación de Home Assistant para la Etapa E.
"""

from pathlib import Path

from automation.stage_e_runtime import build_stage_e_simulation


def print_result(title: str, result) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(result)


def main() -> None:
    storage_path = Path("data/stage_e_manual_automations.json")

    environment = build_stage_e_simulation(
        storage_path=storage_path,
        owner_user_id="REDACTED_f73137d930c3",
    )

    print_result(
        "Estado inicial del simulador",
        environment.simulator.snapshot(),
    )

    # 1. Consultar temperatura.
    temperature_task = environment.manager.create(
        action_id="home.state.read",
        owner_user_id="REDACTED_f73137d930c3",
        creator_user_id="REDACTED_f73137d930c3",
        parameters={
            "entity_id": "sensor.atlas_temperature",
        },
    )

    temperature_result = environment.manager.execute(
        temperature_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
    )

    print_result(
        "Consulta del sensor de temperatura",
        temperature_result,
    )

    # 2. Encender luz virtual.
    light_on_task = environment.manager.create(
        action_id="home.light.turn_on",
        owner_user_id="REDACTED_f73137d930c3",
        creator_user_id="REDACTED_f73137d930c3",
        parameters={
            "entity_id": "light.atlas_virtual",
        },
    )

    light_on_result = environment.manager.execute(
        light_on_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
    )

    print_result(
        "Encendido de luz virtual",
        light_on_result,
    )

    # 3. Apagar luz virtual.
    light_off_task = environment.manager.create(
        action_id="home.light.turn_off",
        owner_user_id="REDACTED_f73137d930c3",
        creator_user_id="REDACTED_f73137d930c3",
        parameters={
            "entity_id": "light.atlas_virtual",
        },
    )

    light_off_result = environment.manager.execute(
        light_off_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
    )

    print_result(
        "Apagado de luz virtual",
        light_off_result,
    )

    # 4. Intentar encender enchufe sin confirmar.
    switch_task = environment.manager.create(
        action_id="home.switch.turn_on",
        owner_user_id="REDACTED_f73137d930c3",
        creator_user_id="REDACTED_f73137d930c3",
        parameters={
            "entity_id": "switch.atlas_virtual",
        },
    )

    switch_pending_result = environment.manager.execute(
        switch_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
    )

    print_result(
        "Enchufe sin confirmación",
        switch_pending_result,
    )

    # 5. Confirmar el encendido.
    switch_confirmed_result = environment.manager.execute(
        switch_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
        confirmed=True,
    )

    print_result(
        "Enchufe con confirmación",
        switch_confirmed_result,
    )

    # 6. Probar una cerradura no registrada.
    lock_task = environment.manager.create(
        action_id="home.state.read",
        owner_user_id="REDACTED_f73137d930c3",
        creator_user_id="REDACTED_f73137d930c3",
        parameters={
            "entity_id": "lock.front_door",
        },
    )

    lock_result = environment.manager.execute(
        lock_task.automation_id,
        requested_by_user_id="REDACTED_f73137d930c3",
        channel="manual_test",
    )

    print_result(
        "Intento de acceder a una cerradura no autorizada",
        lock_result,
    )

    print_result(
        "Estado final del simulador",
        environment.simulator.snapshot(),
    )


if __name__ == "__main__":
    main()