from pathlib import Path

def test_required_files_exist():
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "console" / "command_help.py",
        root / "core" / "atlas_commands.py",
        root / "core" / "atlas.py",
        root / "core" / "guest_session.py",
        root / "core" / "atlas_users.py",
        root / "core" / "atlas_social.py",
        root / "core" / "atlas_family.py",
    ]
    assert all(path.exists() for path in required)

def test_help_context_is_present():
    root = Path(__file__).resolve().parents[1]
    text = (root / "console" / "command_help.py").read_text(encoding="utf-8")
    assert "class HelpAccessContext" in text
    assert "render_help_for_user" in text

def test_commands_use_filtered_help():
    root = Path(__file__).resolve().parents[1]
    text = (root / "core" / "atlas_commands.py").read_text(encoding="utf-8")
    assert "render_help_for_user" in text

def test_identity_and_family_guards_are_present():
    root = Path(__file__).resolve().parents[1]
    users = (root / "core" / "atlas_users.py").read_text(encoding="utf-8")
    social = (root / "core" / "atlas_social.py").read_text(encoding="utf-8")
    family = (root / "core" / "atlas_family.py").read_text(encoding="utf-8")
    assert "_current_interlocutor_name" in users
    assert "_looks_like_family_question" in social
    assert "_handle_family_relation_question" in family
