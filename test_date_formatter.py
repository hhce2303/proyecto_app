"""
Script de prueba para date_formatter.
Muestra ejemplos de cómo se formatean las fechas.
"""
from datetime import datetime, timedelta
from utils.date_formatter import format_friendly_datetime

# Fecha actual
now = datetime.now()

# Ejemplos de fechas
ejemplos = [
    ("HOY (ahora)", now),
    ("HOY (hace 2 horas)", now - timedelta(hours=2)),
    ("AYER", now - timedelta(days=1)),
    ("Hace 3 días", now - timedelta(days=3)),
    ("Hace 5 días", now - timedelta(days=5)),
    ("Hace 7 días", now - timedelta(days=7)),
    ("Hace 10 días", now - timedelta(days=10)),
    ("Hace 30 días", now - timedelta(days=30)),
]

print("=" * 60)
print("EJEMPLOS DE FORMATEO DE FECHAS")
print("=" * 60)
print()

for descripcion, fecha in ejemplos:
    formato_amigable = format_friendly_datetime(fecha, show_seconds=False)
    formato_completo = format_friendly_datetime(fecha, show_seconds=False, force_full=True)
    
    print(f"{descripcion:20} -> {formato_amigable:25} (completo: {formato_completo})")

print()
print("=" * 60)
print("NOTA: El formato cambia automáticamente según la antigüedad:")
print("  - HOY: muestra 'HOY HH:MM AM/PM'")
print("  - AYER: muestra 'AYER HH:MM AM/PM'")
print("  - ESTA SEMANA (2-6 días): muestra 'DÍA HH:MM AM/PM' (LUN, MAR, etc.)")
print("  - MÁS ANTIGUO: muestra 'YYYY-MM-DD HH:MM'")
print("=" * 60)
