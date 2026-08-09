"""Asistente informativo CUDA/cuDNN; no instala ni modifica el sistema."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.stt import _windows_dll_available
from voice.stt_diagnostics import nvidia_summary


def main() -> int:
    print("Asistente de CUDA para faster-whisper (solo lectura)")
    print(f"GPU/driver: {nvidia_summary() or 'no detectado'}")
    required = {
        "cublas64_12.dll": "CUDA Toolkit 12",
        "cudnn64_9.dll": "cuDNN 9 para CUDA 12",
    }
    missing = []
    for library, component in required.items():
        if _windows_dll_available(library):
            print(f"[OK] {library} ({component})")
        else:
            missing.append((library, component))
            print(f"[FALTA] {library} — instala {component}")
    if not missing:
        print("Las bibliotecas requeridas son accesibles. Verifica con: python scripts/check_stt_config.py --load-model")
        return 0
    print("\nPasos manuales recomendados:")
    print("1. Instala CUDA Toolkit 12 desde https://developer.nvidia.com/cuda-downloads")
    print("2. Instala cuDNN 9 desde https://developer.nvidia.com/cudnn-downloads")
    print("3. Reinicia la terminal para que los directorios bin oficiales estén en PATH.")
    print("4. Verifica con: where cublas64_12.dll")
    print("5. Verifica con: where cudnn64_9.dll")
    print("6. Ejecuta: python scripts/check_stt_config.py --load-model")
    print("No copies DLL sueltas ni las descargues de sitios de terceros.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
