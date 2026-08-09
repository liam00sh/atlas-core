"""Ejecución lazy por roles, validación y fallback local ascendente."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ai.models.roles import ModelRole, ModelRoleRegistry
from ai.routing.router import AIRouter, RouteDecision, RoutingRequest
from ai.routing.validator import ResponseValidation, ResponseValidator, ValidationContext
from logger import info


@dataclass(frozen=True, slots=True)
class AIExecutionResult:
    response: str
    initial_role: ModelRole
    final_role: ModelRole
    model: str
    provider: str
    fallback: bool
    fallback_reason: str | None
    route_reason: str
    latency_seconds: float
    validation: str
    attempts: tuple[str, ...]


class AIModelRuntime:
    ORDER = (ModelRole.FAST, ModelRole.REASONING, ModelRole.DEEP)

    def __init__(
        self,
        *,
        providers: dict[ModelRole, object],
        registry: ModelRoleRegistry,
        router: AIRouter | None = None,
        validator: ResponseValidator | None = None,
    ) -> None:
        self.providers = dict(providers)
        self.registry = registry
        self.router = router or AIRouter()
        self.validator = validator or ResponseValidator()

    @classmethod
    def single(cls, provider: object) -> "AIModelRuntime":
        model = str(getattr(provider, "get_model_name")())
        from ai.models.roles import RoleModelDefinition
        definitions = [
            RoleModelDefinition(role, "local", model) for role in cls.ORDER
        ] + [RoleModelDefinition(ModelRole.EXTERNAL, "disabled", None, enabled=False)]
        registry = ModelRoleRegistry(definitions)
        return cls(providers={role: provider for role in cls.ORDER}, registry=registry)

    def provider_for(self, role: ModelRole) -> object:
        try:
            return self.providers[role]
        except KeyError as exc:
            raise RuntimeError(f"No hay proveedor configurado para el rol {role.value}.") from exc

    def _next_roles(self, initial: ModelRole) -> tuple[ModelRole, ...]:
        index = self.ORDER.index(initial)
        return self.ORDER[index:]

    def generate(
        self,
        prompt: str,
        request: RoutingRequest,
        validation_context: ValidationContext,
    ) -> tuple[AIExecutionResult, object]:
        decision: RouteDecision = self.router.route(request)
        started = perf_counter()
        attempts: list[str] = []
        last_validation = ResponseValidation(False, "not_run")
        escalation_reason: str | None = None
        first_role = decision.role

        for role in self._next_roles(first_role):
            provider = self.provider_for(role)
            definition = self.registry.resolve(role)
            model = str(definition.model or getattr(provider, "get_model_name")())
            attempts.append(role.value)
            try:
                installed = getattr(provider, "is_model_installed", None)
                if callable(installed) and not installed():
                    last_validation = ResponseValidation(False, "model_not_installed")
                    escalation_reason = last_validation.reason
                    continue
                response = str(provider.generate(prompt)).strip()
            except (RuntimeError, ValueError) as exc:
                last_validation = ResponseValidation(False, f"provider_error:{type(exc).__name__}")
                escalation_reason = last_validation.reason
                continue

            last_validation = self.validator.validate(response, validation_context)
            if last_validation.sufficient:
                elapsed = perf_counter() - started
                result = AIExecutionResult(
                    response=response,
                    initial_role=first_role,
                    final_role=role,
                    model=model,
                    provider=str(definition.provider),
                    fallback=role is not first_role,
                    fallback_reason=None if role is first_role else escalation_reason,
                    route_reason=decision.reason,
                    latency_seconds=elapsed,
                    validation=last_validation.reason,
                    attempts=tuple(attempts),
                )
                self._log(result)
                return result, provider
            if not last_validation.allow_fallback:
                break
            escalation_reason = last_validation.reason

        elapsed = perf_counter() - started
        safe = last_validation.safe_response or (
            "No he podido obtener una respuesta local suficientemente fiable. "
            "Necesito que reformules la petición o aportes el dato que falta."
        )
        final_role = ModelRole(attempts[-1]) if attempts else first_role
        definition = self.registry.resolve(final_role)
        result = AIExecutionResult(
            response=safe,
            initial_role=first_role,
            final_role=final_role,
            model=str(definition.model or "unavailable"),
            provider=str(definition.provider),
            fallback=final_role is not first_role,
            fallback_reason=last_validation.reason,
            route_reason=decision.reason,
            latency_seconds=elapsed,
            validation=last_validation.reason,
            attempts=tuple(attempts),
        )
        self._log(result)
        return result, self.provider_for(final_role)

    @staticmethod
    def _log(result: AIExecutionResult) -> None:
        info(
            "[AI ROUTER] "
            f"route={result.final_role.value} reason={result.route_reason} "
            f"model={result.model} fallback={str(result.fallback).lower()} "
            f"validation={result.validation} latency={result.latency_seconds:.3f}s"
        )
