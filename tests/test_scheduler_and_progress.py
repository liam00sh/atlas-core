from __future__ import annotations

import threading
import time

from telegram_interface.progress import progress_delay_for
from telegram_interface.scheduler import ConversationJobClassifier, ConversationScheduler


def test_social_messages_have_no_progress():
    assert progress_delay_for("Hola") < 0
    assert progress_delay_for("¿Cómo estás?") < 0
    assert progress_delay_for("¡Muchas gracias!") < 0


def test_non_trivial_progress_waits_until_latency_is_perceptible():
    assert progress_delay_for("Busca en Internet el tiempo") == 4.5
    assert progress_delay_for("Traduce este texto") == 4.5


def test_owner_wins_equal_cost_but_not_over_quick_other_user():
    classifier = ConversationJobClassifier("Alex")
    Alex = classifier.classify("Explícame este tema", "Alex")
    alias_ejemplo_44_01 = classifier.classify("Explícame este tema", "Vega")
    Carla_quick = classifier.classify("Gracias", "Carla")
    assert Alex.owner_bonus > alias_ejemplo_44_01.owner_bonus
    assert Carla_quick.lane == "quick"
    assert Alex.lane == "core"


def test_same_session_keeps_fifo_order():
    scheduler = ConversationScheduler(owner_user_id="Alex", quick_workers=1)
    done = []
    event = threading.Event()

    def submit(label):
        scheduler.submit(
            user_id="Carla",
            session_id="Carla-chat",
            text="Explícame algo",
            run=lambda: label,
            on_done=lambda result: (done.append(result), event.set() if len(done) == 2 else None),
            on_error=lambda exc: (_ for _ in ()).throw(exc),
        )

    submit("primero")
    submit("segundo")
    assert event.wait(2.0)
    scheduler.stop()
    assert done == ["primero", "segundo"]


def test_quick_lane_finishes_while_core_lane_is_busy():
    scheduler = ConversationScheduler(owner_user_id="Alex", quick_workers=1)
    finished = []
    event = threading.Event()

    scheduler.submit(
        user_id="Alex",
        session_id="Alex",
        text="Analiza este PDF de 300 páginas",
        run=lambda: (time.sleep(0.25), "pesada")[1],
        on_done=lambda result: finished.append(result),
        on_error=lambda exc: None,
    )
    scheduler.submit(
        user_id="Carla",
        session_id="Carla",
        text="Gracias",
        run=lambda: "rapida",
        on_done=lambda result: (finished.append(result), event.set()),
        on_error=lambda exc: None,
    )
    assert event.wait(1.0)
    scheduler.stop()
    assert finished[0] == "rapida"
