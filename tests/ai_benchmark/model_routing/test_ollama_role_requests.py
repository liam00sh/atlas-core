from ai.providers.ollama_provider import OllamaProvider


def _capture_payload(monkeypatch, model):
    provider = OllamaProvider(model)
    captured = {}
    monkeypatch.setattr(provider, "is_model_installed", lambda: True)

    def request(*, path, method="GET", payload=None):
        captured.update({"path": path, "method": method, "payload": payload})
        return {"thinking": "razonamiento privado", "response": "Respuesta final"}

    monkeypatch.setattr(provider, "_request_json", request)
    assert provider.generate("Pregunta") == "Respuesta final"
    return captured["payload"]


def test_qwen3_deep_keeps_thinking_separate_from_the_final_answer(monkeypatch):
    payload = _capture_payload(monkeypatch, "qwen3:30b")
    assert payload["think"] is True
    assert payload["prompt"] == "Pregunta"


def test_qwen25_keeps_its_normal_prompt(monkeypatch):
    payload = _capture_payload(monkeypatch, "qwen2.5:7b")
    assert payload["think"] is False
    assert payload["prompt"] == "Pregunta"
