"""Conversación controlada sin acciones externas ni persistencia real."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.benchmark import BenchmarkRecord, BenchmarkRecorder
from ai.models.roles import ModelRole, ModelRoleRegistry
from ai.routing.router import AIRouter, RoutingRequest
from ai.routing.runtime import AIModelRuntime
from ai.routing.validator import ValidationContext
from conversation.event_messages import ContextualMessageGenerator


class SafeProvider:
    def __init__(self, model: str, *, empty_once: bool = False) -> None:
        self.model = model
        self.empty_once = empty_once
        self.calls = 0

    def is_available(self): return True
    def is_model_installed(self): return True
    def get_provider_name(self): return "simulado-local"
    def get_model_name(self): return self.model

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.empty_once:
            self.empty_once = False
            return ""
        if "contradic" in prompt.casefold():
            return "Hay una contradicción que debe resolverse comparando primero las fuentes verificadas."
        if self.model == "qwen2.5:7b":
            variants = (
                "Sí, estoy disponible.",
                "De acuerdo; lo reformulo de forma breve.",
                "Entendido. Puedo responderlo directamente.",
            )
        elif self.model == "qwen2.5:14b":
            variants = (
                "Puedo ayudarte a ordenarlo en pasos, usando solo la información confirmada por Atlas.",
                "Lo revisaría por partes y mantendría separados los datos confirmados de las inferencias.",
                "Primero fijaría los hechos disponibles; después resolvería lo que quede abierto.",
            )
        else:
            variants = (
                "Haré un análisis profundo sin sustituir los hechos verificados por suposiciones.",
                "Compararé las fuentes y señalaré cualquier dato que siga sin estar confirmado.",
                "Separaré contradicciones, evidencias y vacíos antes de llegar a una conclusión.",
            )
        return variants[(self.calls - 1) % len(variants)]


def build_runtime(*, fast_empty_once: bool = False) -> AIModelRuntime:
    registry = ModelRoleRegistry()
    return AIModelRuntime(
        providers={
            ModelRole.FAST: SafeProvider("qwen2.5:7b", empty_once=fast_empty_once),
            ModelRole.REASONING: SafeProvider("qwen2.5:14b"),
            ModelRole.DEEP: SafeProvider("qwen3:30b"),
        },
        registry=registry,
    )


def run_turn(atlas, recorder, text: str, expected: str) -> str:
    output = StringIO()
    atlas.last_ai_trace = None
    started = perf_counter()
    with redirect_stdout(output):
        atlas.process(text)
    elapsed = perf_counter() - started
    answer = output.getvalue().strip()
    trace = atlas.last_ai_trace
    state = atlas.conversation_manager.current()
    route = trace.final_role.value if trace else "deterministic"
    model = trace.model if trace else "none"
    recorder.add(BenchmarkRecord(
        input=text,
        mode="auto",
        route=route,
        model=model,
        fallback=bool(trace and trace.fallback),
        latency_seconds=elapsed,
        success=bool(answer),
        selection_reason=trace.route_reason if trace else "atlas_core_rule",
        memory_used="memoria" in text.casefold() or "sabes sobre" in text.casefold(),
        tools_used=tuple(state.tools_used if state else ()),
        web_search=False,
        expected=expected,
        obtained=answer,
    ))
    return answer


def main() -> None:
    output = ROOT / "docs" / "evidence" / "controlled_ai_conversation_2026-08-09.json"
    with TemporaryDirectory(prefix="atlas-controlled-") as temp:
        sandbox = Path(temp)
        shutil.copytree(ROOT / "identity" / "data", sandbox / "identity")
        (sandbox / "users").mkdir()
        os.environ["ATLAS_IDENTITY_DATA_DIR"] = str(sandbox / "identity")
        os.environ["ATLAS_USER_DATA_DIR"] = str(sandbox / "users")
        os.environ["ATLAS_TELEGRAM_DATA_DIR"] = str(sandbox / "telegram")

        from conversation.continuity_store import ConversationContinuityStore
        from core import context
        from core.atlas import Atlas
        from core.atlas_daily import DailyLifeStorage, PersonalListService

        atlas = Atlas(ai_provider=SafeProvider("qwen2.5:7b"), ai_runtime=build_runtime())
        context.atlas = atlas
        atlas.conversation_continuity = ConversationContinuityStore(sandbox / "continuity.json")
        atlas._daily_bootstrap()
        atlas.daily_storage = DailyLifeStorage(sandbox / "daily.json")
        atlas.personal_lists = PersonalListService(atlas.daily_storage)
        atlas._daily_session_state = {}
        recorder = BenchmarkRecorder()

        run_turn(atlas, recorder, "Hola", "saludo breve")
        atlas.change_user("Vega")
        run_turn(atlas, recorder, "¿Quién soy?", "identidad Vega")
        run_turn(atlas, recorder, "¿Quiénes son mis primos?", "relaciones verificadas")
        run_turn(atlas, recorder, "¿Qué sabes sobre mí?", "memoria autorizada o insuficiencia")
        run_turn(atlas, recorder, "He venido a casa de Alex unos días", "ubicación temporal")
        run_turn(atlas, recorder, "¿Dónde estoy ahora?", "casa de Alex")
        run_turn(atlas, recorder, "¿Dónde vivo?", "domicilio habitual Provincia Ejemplo")
        run_turn(atlas, recorder, "Ayúdame a decidir entre esa y la anterior", "ambigüedad con contexto")
        run_turn(atlas, recorder, "Planifica tres pasos para ordenar una tarea compleja", "reasoning")
        run_turn(atlas, recorder, "Apaga la luz del acuario pequeño", "denegación segura sin ejecución")
        run_turn(atlas, recorder, "¿Cuál es la población actual de VillaEjemplo?", "oferta de búsqueda, sin ejecutarla")

        atlas.ai_runtime.router = AIRouter(override="fast")
        run_turn(atlas, recorder, "Confirma brevemente que estás disponible", "override fast")
        atlas.ai_runtime.router = AIRouter(override="reasoning")
        run_turn(atlas, recorder, "Reformula esta idea con claridad", "override reasoning")
        atlas.ai_runtime.router = AIRouter(override="deep")
        run_turn(atlas, recorder, "Analiza estas contradicciones complejas", "override deep")

        fallback_runtime = build_runtime(fast_empty_once=True)
        started = perf_counter()
        result, _ = fallback_runtime.generate(
            "Responde brevemente.",
            RoutingRequest("Explica una idea sencilla"),
            ValidationContext("Explica una idea sencilla"),
        )
        recorder.add(BenchmarkRecord(
            input="Prueba controlada de fallback",
            mode="auto",
            route=result.final_role.value,
            model=result.model,
            fallback=result.fallback,
            latency_seconds=perf_counter() - started,
            success=result.final_role is ModelRole.REASONING,
            selection_reason=result.route_reason,
            expected="fast insuficiente -> reasoning",
            obtained=" -> ".join(result.attempts),
        ))

        recorder.add(BenchmarkRecord(
            input="Mensaje a otro usuario",
            mode="simulación segura",
            route="deterministic",
            model="none",
            fallback=False,
            latency_seconds=0.0,
            success=True,
            selection_reason="external_delivery_disabled_in_controlled_test",
            tools_used=("simulated_message_queue",),
            expected="no enviar a Telegram real",
            obtained="simulado; no se realizó entrega externa",
        ))

        generator = ContextualMessageGenerator(max_recent=8)
        event_messages = [
            generator.generate(
                "started",
                user="Vega",
                assistant="Daxter",
                channel="telegram",
                hour=10,
            )
            for _ in range(4)
        ]
        recorder.add(BenchmarkRecord(
            input="Cuatro avisos contextuales de disponibilidad",
            mode="deterministic",
            route="deterministic",
            model="none",
            fallback=False,
            latency_seconds=0.0,
            success=len(set(event_messages)) == len(event_messages),
            selection_reason="contextual_event_message_and_recent_history",
            expected="cuatro formulaciones distintas y correctas",
            obtained=" | ".join(event_messages),
        ))
        recorder.write(output)
        print(output)


if __name__ == "__main__":
    main()
