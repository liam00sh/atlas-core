"""Planificador de automatizaciones pendientes."""
from __future__ import annotations

from automation.models import AutomationStatus, utc_now


class AutomationScheduler:
    def __init__(self, executor):
        self.executor = executor

    def run_due(
        self,
        automations,
        requested_by_user_id,
        channel,
        now=None,
    ):
        current = now or utc_now()
        results = []
        for automation in automations:
            if automation.status != AutomationStatus.SCHEDULED:
                continue
            if automation.scheduled_for is None or automation.scheduled_for > current:
                continue
            results.append(
                self.executor.execute(
                    automation,
                    requested_by_user_id=automation.owner_user_id,
                    channel=channel,
                    confirmed=True,
                )
            )
        return results
