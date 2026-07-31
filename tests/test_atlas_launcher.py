from __future__ import annotations

import importlib.util
from pathlib import Path


def test_launcher_exists():
    path = Path("atlas_launcher.py")
    assert path.is_file()


def test_launcher_imports():
    import sys

    spec = importlib.util.spec_from_file_location(
        "atlas_launcher",
        "atlas_launcher.py",
    )
    assert spec is not None

    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None

    # Python 3.14 y dataclasses necesitan que el módulo esté registrado
    # en sys.modules durante exec_module cuando se usan anotaciones
    # aplazadas mediante ``from __future__ import annotations``.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)


def test_main_background_entrypoint_exists():
    import main

    assert callable(main.build_atlas)
    assert callable(main.main_background)
    assert callable(main.cli)
