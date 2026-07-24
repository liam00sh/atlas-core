from automation.home_assistant_models import HomeEntityMode
from automation.stage_e_runtime import _real_lab_entities


def test_physical_mode_has_real_alias():
    assert HomeEntityMode.REAL is HomeEntityMode.PHYSICAL


def test_real_catalog_contains_aquarium_entities():
    entity_ids = {entity.entity_id for entity in _real_lab_entities()}
    assert "switch.salon_acuario_grande_luz_acuario_grande" in entity_ids
    assert "switch.despacho_acuario_pequeno_luz_acuario_pequeno" in entity_ids
    assert "switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno" in entity_ids
