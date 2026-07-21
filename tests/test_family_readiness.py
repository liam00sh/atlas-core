from core.atlas_family import _plain


def test_plain_normalizes_accents():
    assert _plain("¿Qué has entendido?") == "que has entendido"


def test_cancel_variants_are_normalizable():
    assert _plain("Olvida lo anterior") == "olvida lo anterior"
