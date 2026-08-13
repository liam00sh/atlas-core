from tools.run_voice_e2e_guided import phrases


def test_guided_e2e_keeps_confirmation_and_cancel_adjacent():
    guided_phrases = phrases(known_name="persona de prueba")
    assert len(guided_phrases) == 13
    restart = guided_phrases.index("Reinicia Telegram.")
    assert guided_phrases[restart + 1] == "Cancelar."
    assert "Saluda a persona de prueba." in guided_phrases
    assert any("acuario pequeño" in phrase for phrase in guided_phrases)
