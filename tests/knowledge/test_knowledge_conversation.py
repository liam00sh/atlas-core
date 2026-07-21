from knowledge.conversation import KnowledgeIntentRecognizer


def test_recognizes_natural_unified_questions():
    recognizer = KnowledgeIntentRecognizer()
    for text in (
        "¿Qué sabes sobre mi familia?",
        "¿Qué información tienes sobre Saray?",
        "¿Cómo quiero que funcione la memoria de Atlas?",
        "¿Qué hemos decidido sobre la privacidad?",
        "Resume lo que sabes sobre la arquitectura de Atlas.",
        "¿Hay información contradictoria sobre esta persona?",
    ):
        assert recognizer.recognize(text) is not None


def test_provenance_followup_is_structured():
    intent = KnowledgeIntentRecognizer().recognize("¿De dónde sabes eso?")
    assert intent is not None
    assert intent.provenance_only is True


def test_unrelated_conversation_is_not_intercepted():
    assert KnowledgeIntentRecognizer().recognize("Hola, ¿cómo estás?") is None


def test_explicit_sensitive_question_is_marked_but_not_authorized():
    intent = KnowledgeIntentRecognizer().recognize("¿Qué información tienes sobre mi DNI?")
    assert intent is not None
    assert intent.allow_sensitive is True


def test_recognizes_additional_natural_variants():
    recognizer = KnowledgeIntentRecognizer()
    for text in (
        "Hablame de Saray.",
        "Dime todo lo que recuerdas de mi familia.",
        "Cuentame lo que sabes acerca de la privacidad.",
        "Que recuerdas sobre el acceso a Internet?",
        "Junta lo que sabes sobre la arquitectura de Atlas.",
    ):
        assert recognizer.recognize(text) is not None
