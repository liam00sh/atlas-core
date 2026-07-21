"""Planificador conversacional seguro para solicitudes multiusuario.

No intenta ejecutar en paralelo el núcleo mutable de Atlas. Mantiene un único
worker de Core y permite workers rápidos para respuestas deterministas. Las
peticiones se ordenan por prioridad efectiva con envejecimiento, ligera ventaja
para el propietario y protección FIFO dentro de cada sesión.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
import re
import threading
import time
import unicodedata
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@dataclass(slots=True)
class JobProfile:
    kind: str
    estimated_cost: int
    base_priority: float
    lane: str
    owner_bonus: float = 0.0
    management_bonus: float = 0.0


@dataclass(slots=True)
class ConversationJob(Generic[T]):
    job_id: int
    user_id: str
    session_id: str
    text: str
    created_at: float
    profile: JobProfile
    run: Callable[[], T]
    on_done: Callable[[T], None]
    on_error: Callable[[BaseException], None]
    sequence: int = 0
    cancelled: bool = False


class ConversationJobClassifier:
    """Clasificación conservadora para decidir cola, coste y prioridad."""

    QUICK_EXACT = {
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
        "como estas", "que tal", "gracias", "muchas gracias", "vale", "ok",
        "de acuerdo", "adios", "hasta luego", "perfecto",
    }
    MANAGEMENT_MARKERS = (
        "estado de atlas", "reinicia atlas", "deten atlas", "inicia atlas",
        "configura atlas", "actualiza atlas", "amplia atlas", "gestiona atlas",
        "anade usuario", "añade usuario", "vincula telegram", "desvincula telegram",
        "permisos de atlas", "copia de seguridad", "restaura copia",
    )
    MEMORY_MARKERS = (
        "que recuerdas", "qué recuerdas", "que sabes de mi", "qué sabes de mí",
        "recuerda", "olvida", "memoria", "recuerdo",
    )
    INTERNET_MARKERS = (
        "busca en internet", "consulta en internet", "busca online",
        "investiga en la web", "busca en la web",
    )
    TRANSLATION_MARKERS = ("traduce", "traducir", "como se dice", "cómo se dice")
    HEAVY_MARKERS = (
        "resume este pdf", "analiza este pdf", "analiza drive", "indexa drive",
        "reindexa", "informe completo", "analiza este documento", "documento largo",
    )

    def __init__(self, owner_user_id: str = "Liam") -> None:
        self.owner_user_id = owner_user_id.casefold()

    def classify(self, text: str, user_id: str) -> JobProfile:
        normalized = _plain(text)
        owner_bonus = 0.35 if user_id.casefold() == self.owner_user_id else 0.0
        management = any(marker in normalized for marker in map(_plain, self.MANAGEMENT_MARKERS))
        management_bonus = 1.6 if management else 0.0

        if normalized in self.QUICK_EXACT:
            return JobProfile("social_quick", 1, 10.0, "quick", owner_bonus, management_bonus)
        if management:
            return JobProfile("management", 3, 9.2, "core", owner_bonus, management_bonus)
        if any(_plain(marker) in normalized for marker in self.MEMORY_MARKERS):
            return JobProfile("memory", 2, 8.2, "core", owner_bonus, management_bonus)
        if any(_plain(marker) in normalized for marker in self.TRANSLATION_MARKERS):
            return JobProfile("translation", 5, 6.7, "core", owner_bonus, management_bonus)
        if any(_plain(marker) in normalized for marker in self.INTERNET_MARKERS):
            return JobProfile("internet", 7, 5.8, "core", owner_bonus, management_bonus)
        if any(_plain(marker) in normalized for marker in self.HEAVY_MARKERS):
            return JobProfile("heavy", 10, 4.2, "core", owner_bonus, management_bonus)
        if len(normalized) <= 45:
            return JobProfile("short", 2, 7.5, "core", owner_bonus, management_bonus)
        if len(normalized) <= 220:
            return JobProfile("medium", 4, 6.3, "core", owner_bonus, management_bonus)
        return JobProfile("long", 7, 5.0, "core", owner_bonus, management_bonus)


class ConversationScheduler:
    """Priority queue con aging, FIFO por sesión y dos lanes.

    - lane ``core``: un worker, porque AtlasCoreAdapter protege un núcleo mutable.
    - lane ``quick``: dos workers para respuestas deterministas que no usan Ollama.
    - aging: cada segundo de espera aumenta ligeramente la prioridad.
    - owner bonus: Liam gana empates de coste/prioridad, pero no bloquea tareas rápidas.
    """

    def __init__(
        self,
        *,
        owner_user_id: str = "Liam",
        quick_workers: int = 2,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.classifier = ConversationJobClassifier(owner_user_id)
        self.clock = clock
        self._counter = count(1)
        self._session_sequence: dict[str, int] = {}
        self._session_active: set[str] = set()
        self._session_waiting: dict[str, list[ConversationJob]] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._core_queue: list[ConversationJob] = []
        self._quick_queue: list[ConversationJob] = []
        self._condition = threading.Condition(self._lock)
        self._threads: list[threading.Thread] = []
        self._start_worker("core", self._core_queue)
        for index in range(max(1, quick_workers)):
            self._start_worker(f"quick-{index+1}", self._quick_queue)

    def _start_worker(self, name: str, queue: list[ConversationJob]) -> None:
        thread = threading.Thread(target=self._worker, args=(queue,), name=f"atlas-scheduler-{name}", daemon=True)
        thread.start()
        self._threads.append(thread)

    def submit(
        self,
        *,
        user_id: str,
        session_id: str,
        text: str,
        run: Callable[[], T],
        on_done: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> ConversationJob[T]:
        profile = self.classifier.classify(text, user_id)
        with self._lock:
            seq = self._session_sequence.get(session_id, 0) + 1
            self._session_sequence[session_id] = seq
            job = ConversationJob(
                job_id=next(self._counter),
                user_id=user_id,
                session_id=session_id,
                text=text,
                created_at=self.clock(),
                profile=profile,
                run=run,
                on_done=on_done,
                on_error=on_error,
                sequence=seq,
            )
            if session_id in self._session_active:
                self._session_waiting.setdefault(session_id, []).append(job)
            else:
                self._session_active.add(session_id)
                self._enqueue(job)
            return job

    def _priority_key(self, job: ConversationJob) -> float:
        waited = max(0.0, self.clock() - job.created_at)
        aging = min(6.0, waited * 0.12)
        effective = (
            job.profile.base_priority
            + job.profile.owner_bonus
            + job.profile.management_bonus
            + aging
            - (job.profile.estimated_cost * 0.18)
        )
        return -effective

    def _enqueue(self, job: ConversationJob) -> None:
        queue = self._quick_queue if job.profile.lane == "quick" else self._core_queue
        queue.append(job)
        self._condition.notify_all()

    def _take_next(self, queue: list[ConversationJob]) -> ConversationJob | None:
        with self._condition:
            while not self._stop.is_set() and not queue:
                self._condition.wait(timeout=0.2)
            if self._stop.is_set() or not queue:
                return None
            # Recalcular en cada extracción hace que el envejecimiento sea real.
            index = min(
                range(len(queue)),
                key=lambda item: (self._priority_key(queue[item]), queue[item].job_id),
            )
            return queue.pop(index)

    def _worker(self, queue: list[ConversationJob]) -> None:
        while not self._stop.is_set():
            job = self._take_next(queue)
            if job is None:
                continue
            try:
                if not job.cancelled:
                    result = job.run()
                    job.on_done(result)
            except BaseException as exc:  # callback de error controlado
                try:
                    job.on_error(exc)
                except Exception:
                    pass
            finally:
                self._release_session(job.session_id)

    def _release_session(self, session_id: str) -> None:
        with self._lock:
            waiting = self._session_waiting.get(session_id)
            if waiting:
                next_job = waiting.pop(0)
                if not waiting:
                    self._session_waiting.pop(session_id, None)
                self._enqueue(next_job)
            else:
                self._session_active.discard(session_id)

    def stop(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify_all()

    def pending_count(self) -> int:
        with self._lock:
            blocked = sum(len(items) for items in self._session_waiting.values())
        return len(self._core_queue) + len(self._quick_queue) + blocked
