"""Contrato del registro de modelos consumido por Atlas."""

import pytest

import config
from ai.models import ModelDefinition, ModelRegistry


def test_default_registry_uses_documented_ollama_model():
    registry = ModelRegistry()

    assert registry.get_default_model_name() == "qwen2.5:7b"
    assert registry.get_default_provider_name() == "ollama"
    assert registry.resolve() == ModelDefinition("qwen2.5:7b", "ollama")


def test_registry_registers_resolves_and_selects_models():
    registry = ModelRegistry()

    added = registry.register("local-test:1b", "ollama", make_default=True)

    assert registry.resolve("local-test:1b") is added
    assert registry.get_default_model_name() == "local-test:1b"
    assert added in registry.list_models(provider="OLLAMA")


def test_registry_rejects_unknown_and_duplicate_models():
    registry = ModelRegistry()

    with pytest.raises(KeyError, match="Modelo no registrado"):
        registry.resolve("missing:model")
    assert registry.list_models(provider="missing-provider") == ()
    with pytest.raises(ValueError, match="ya está registrado"):
        registry.register("qwen2.5:7b", "ollama")


def test_registry_honours_central_model_configuration(monkeypatch):
    monkeypatch.setattr(config, "AI_MODEL", "configured:3b")
    monkeypatch.setattr(config, "AI_PROVIDER", "ollama")

    registry = ModelRegistry()

    assert registry.get_default_model_name() == "configured:3b"
    assert registry.resolve().provider == "ollama"


def test_main_build_atlas_passes_registry_default_to_provider(monkeypatch):
    import main

    captured = {}

    class FakeRegistry:
        def get_default_model_name(self):
            return "consumer-test:7b"

    class FakeProvider:
        def __init__(self, *, model_name, timeout):
            captured.update(model_name=model_name, timeout=timeout)

    class FakeAtlas:
        def __init__(self, *, ai_provider):
            self.ai_provider = ai_provider

    monkeypatch.setattr(main, "ModelRegistry", FakeRegistry)
    monkeypatch.setattr(main, "OllamaProvider", FakeProvider)
    monkeypatch.setattr(main, "Atlas", FakeAtlas)

    atlas = main.build_atlas()

    assert captured == {"model_name": "consumer-test:7b", "timeout": 180}
    assert atlas.ai_provider is main.context.atlas.ai_provider
