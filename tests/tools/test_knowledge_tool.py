from knowledge.fragment import KnowledgeFragment
from knowledge.retriever import CallableKnowledgeSource, KnowledgeRetriever
from knowledge.service import KnowledgeService
from tools.capability import Capability
from tools.context import ToolContext
from tools.knowledge import KnowledgeTool


class Provider:
    def __init__(self, available=True):
        self.available = available
        self.prompt = ""

    def is_available(self):
        return self.available

    def generate(self, prompt):
        self.prompt = prompt
        return "Respuesta basada en [MEMORIA 1]."


def build_tool(provider=None, sensitive=False):
    item = KnowledgeFragment("memory", "m1", "Memoria", "dato conocido", 2, sensitive=sensitive)
    source = CallableKnowledgeSource("memory", lambda **_: [item])
    return KnowledgeTool(KnowledgeService(KnowledgeRetriever([source]), provider))


def context(*permissions):
    return ToolContext(requested_by="Liam", channel="cli", permissions=set(permissions))


def test_retrieve_returns_structured_provenance():
    result = build_tool().execute(Capability("knowledge.retrieve"), {"question": "que sabes"}, context("knowledge.read"))
    assert result.success
    assert result.data["fragments"][0]["source_type"] == "memory"


def test_answer_uses_local_provider_and_sources():
    provider = Provider()
    result = build_tool(provider).execute(Capability("knowledge.answer"), {"question": "que sabes"}, context("knowledge.read"))
    assert result.success
    assert "[MEMORIA 1]" in provider.prompt
    assert result.data["sources"]


def test_provider_unavailable_is_reported_without_exception():
    result = build_tool(Provider(False)).execute(Capability("knowledge.answer"), {"question": "que sabes"}, context("knowledge.read"))
    assert result.success
    assert result.data["insufficient"] is True
    assert "no esta disponible" in result.data["answer"]


def test_explicit_sensitive_query_requires_separate_permission():
    result = build_tool(sensitive=True).execute(
        Capability("knowledge.retrieve"),
        {"question": "muestra el dato", "allow_sensitive": True},
        context("knowledge.read"),
    )
    assert result.success is False
    assert result.error == "sensitive_permission_denied"


def test_provider_generation_error_is_structured():
    class FailingProvider(Provider):
        def generate(self, prompt):
            raise RuntimeError("Ollama disconnected")

    result = build_tool(FailingProvider()).execute(
        Capability("knowledge.answer"),
        {"question": "que sabes"},
        context("knowledge.read"),
    )

    assert result.success
    assert result.data["insufficient"] is True
    assert "no esta disponible" in result.data["answer"]


def test_empty_provider_answer_is_rejected():
    class EmptyProvider(Provider):
        def generate(self, prompt):
            return "   "

    result = build_tool(EmptyProvider()).execute(
        Capability("knowledge.answer"),
        {"question": "que sabes"},
        context("knowledge.read"),
    )

    assert result.success
    assert result.data["insufficient"] is True
    assert "no ha generado" in result.data["answer"]
