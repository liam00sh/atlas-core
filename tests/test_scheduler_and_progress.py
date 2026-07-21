from __future__ import annotations

import threading
import time

from telegram_interface.progress import progress_delay_for
from telegram_interface.scheduler import ConversationJobClassifier, ConversationScheduler


def test_social_messages_have_no_progress():
    assert progress_delay_for("Hola") < 0
    assert progress_delay_for("¿Cómo estás?") < 0
    assert progress_delay_for("¡Muchas gracias!") < 0


def test_non_trivial_progress_waits_four_seconds():
    assert progress_delay_for("Busca en Internet el tiempo") == 4.0
    assert progress_delay_for("Traduce este texto") == 4.0


def test_owner_wins_equal_cost_but_not_over_quick_other_user():
    classifier = ConversationJobClassifier("REDACTED_2c7b6821719d")
    REDACTED_f73137d930c3 = classifier.classify("Explícame este tema", "REDACTED_2c7b6821719d")
    REDACTED_7b9528898599 = classifier.classify("Explícame este tema", "REDACTED_bc04a68d9192")
    REDACTED_6915771be1c5_quick = classifier.classify("Gracias", "REDACTED_aebac53c46bb")
    assert REDACTED_f73137d930c3.owner_bonus > REDACTED_7b9528898599.owner_bonus
    assert REDACTED_6915771be1c5_quick.lane == "quick"
    assert REDACTED_f73137d930c3.lane == "core"


def test_same_session_keeps_fifo_order():
    scheduler = ConversationScheduler(owner_user_id="REDACTED_2c7b6821719d", quick_workers=1)
    done = []
    event = threading.Event()

    def submit(label):
        scheduler.submit(
            user_id="REDACTED_aebac53c46bb",
            session_id="REDACTED_6915771be1c5-chat",
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
    scheduler = ConversationScheduler(owner_user_id="REDACTED_2c7b6821719d", quick_workers=1)
    finished = []
    event = threading.Event()

    scheduler.submit(
        user_id="REDACTED_2c7b6821719d",
        session_id="REDACTED_f73137d930c3",
        text="Analiza este PDF de 300 páginas",
        run=lambda: (time.sleep(0.25), "pesada")[1],
        on_done=lambda result: finished.append(result),
        on_error=lambda exc: None,
    )
    scheduler.submit(
        user_id="REDACTED_aebac53c46bb",
        session_id="REDACTED_6915771be1c5",
        text="Gracias",
        run=lambda: "rapida",
        on_done=lambda result: (finished.append(result), event.set()),
        on_error=lambda exc: None,
    )
    assert event.wait(1.0)
    scheduler.stop()
    assert finished[0] == "rapida"
