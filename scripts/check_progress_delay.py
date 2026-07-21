"""Comprobación manual del umbral de progreso desde PowerShell."""
from telegram_interface.progress import progress_delay_for

SAMPLES = ("Hola", "¿Cómo estás?", "Gracias", "Busca en Internet población de Alicante")
for sample in SAMPLES:
    print(f"{sample!r}: {progress_delay_for(sample)}")
