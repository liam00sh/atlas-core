"""
Autoriza Google Drive para Atlas mediante OAuth 2.0.

Uso:
    python scripts/configure_google_drive.py
"""

from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from tools.google_drive_oauth import (  # noqa: E402
    GoogleDriveOAuthConfig,
    GoogleDriveOAuthProvider,
)


def main() -> int:
    config = GoogleDriveOAuthConfig.default(
        PROJECT_ROOT
    )

    print("Proyecto Atlas — autorización de Google Drive")
    print()
    print(
        "Credenciales esperadas en:"
    )
    print(config.credentials_path)
    print()
    print(
        "El acceso solicitado es exclusivamente de lectura."
    )

    provider = GoogleDriveOAuthProvider(
        config
    )

    try:
        client = provider.build_client(
            interactive=True
        )
    except Exception as exception:
        print()
        print(
            "No se pudo configurar Google Drive:"
        )
        print(exception)
        return 1

    if client is None:
        print(
            "No se obtuvo un cliente de Google Drive."
        )
        return 1

    print()
    print(
        "Google Drive ha quedado autorizado correctamente."
    )
    print(
        "El token local se ha guardado en:"
    )
    print(config.token_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
