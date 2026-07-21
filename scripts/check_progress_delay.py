"""Comprobación manual del umbral de progreso desde PowerShell."""
from telegram_interface.progress import progress_delay_for

SAMPLES = ("Hola", "¿Cómo estás?", "Gracias", "Busca en Internet población de REDACTED_4cde1bf18b9c")
for sample in SAMPLES:
    print(f"{sample!r}: {progress_delay_for(sample)}")
