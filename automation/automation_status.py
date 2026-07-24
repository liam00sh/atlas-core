from automation.models import Automation, AutomationStatus

class AutomationStatusService:
    def transition(self, automation: Automation, status: AutomationStatus) -> Automation:
        automation.status = status
        automation.touch()
        return automation
