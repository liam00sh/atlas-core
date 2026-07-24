"""Rutinas técnicas formadas únicamente por acciones cerradas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True, frozen=True)
class RoutineStep:
    step_id: str
    runner: Callable[[dict[str, Any]], Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    continue_on_error: bool = False


@dataclass(slots=True, frozen=True)
class TechnicalRoutine:
    routine_id: str
    name: str
    steps: tuple[RoutineStep, ...]


class TechnicalRoutineRegistry:
    def __init__(self) -> None:
        self._routines: dict[str, TechnicalRoutine] = {}

    def register(self, routine: TechnicalRoutine) -> None:
        if not routine.routine_id.strip():
            raise ValueError("routine_id no puede estar vacío.")
        if not routine.steps:
            raise ValueError("Una rutina debe contener al menos un paso.")
        if routine.routine_id in self._routines:
            raise ValueError(
                f"La rutina '{routine.routine_id}' ya está registrada."
            )
        self._routines[routine.routine_id] = routine

    def run(self, routine_id: str) -> dict[str, Any]:
        try:
            routine = self._routines[routine_id]
        except KeyError as exc:
            raise LookupError(f"Rutina no registrada: {routine_id}") from exc

        results: list[dict[str, Any]] = []
        success = True
        for step in routine.steps:
            try:
                output = step.runner(dict(step.parameters))
                results.append({
                    "step_id": step.step_id,
                    "success": True,
                    "result": output,
                })
            except Exception as exc:
                success = False
                results.append({
                    "step_id": step.step_id,
                    "success": False,
                    "error_code": type(exc).__name__,
                })
                if not step.continue_on_error:
                    break

        return {
            "routine_id": routine.routine_id,
            "name": routine.name,
            "success": success,
            "steps": results,
        }
