from telegram_interface.lifecycle import TelegramLifecycleNotifier


class Storage:
    def __init__(self):
        self.data = {"accounts": {"1": {"state": "linked", "chat_id": "10", "atlas_user_id": "Liam"}}, "lifecycle": {}}
    def section(self, name):
        return dict(self.data.get(name, {}))
    def update(self, mutator):
        return mutator(self.data)


class Client:
    def __init__(self): self.messages = []
    def send_message(self, *, chat_id, text, parse_mode=None):
        self.messages.append((chat_id, text)); return {}


def test_lifecycle_sends_linked_accounts():
    storage, client = Storage(), Client()
    notifier = TelegramLifecycleNotifier(storage, client, lambda _: "Daxter")
    assert notifier.notify_started() == 1
    assert client.messages
