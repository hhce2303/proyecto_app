# -*- coding: utf-8 -*-
"""
Prueba de corrección del error de tipo en send_to_supervisor
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from datetime import datetime
from utils.timezone_adjuster import adjust_datetime, adjust_description_timestamps

print("="*80)
print("PRUEBA DE CORRECCIÓN: adjust_datetime con strings y datetime")
print("="*80)

# Caso 1: datetime object (original)
print("\n📝 Caso 1: datetime object")
dt_obj = datetime(2025, 12, 16, 14, 30, 0)
print(f"  Entrada: {dt_obj} (tipo: {type(dt_obj).__name__})")
result = adjust_datetime(dt_obj, "MT")
print(f"  Resultado: {result} (offset MT: -2h)")
print(f"  ✅ FUNCIONA" if result.hour == 12 else "  ❌ ERROR")

# Caso 2: string ISO (nuevo soporte)
print("\n📝 Caso 2: string ISO")
dt_str = "2025-12-16 14:30:00"
print(f"  Entrada: '{dt_str}' (tipo: {type(dt_str).__name__})")
result = adjust_datetime(dt_str, "MT")
print(f"  Resultado: {result} (offset MT: -2h)")
print(f"  ✅ FUNCIONA" if result.hour == 12 else "  ❌ ERROR")

# Caso 3: adjust_description_timestamps con datetime
print("\n📝 Caso 3: adjust_description_timestamps con datetime object")
desc = "Event at 14:30 and [02:35]"
dt_obj = datetime(2025, 12, 16, 14, 30, 0)
print(f"  Descripción: '{desc}'")
print(f"  Base datetime: {dt_obj} (tipo: {type(dt_obj).__name__})")
result = adjust_description_timestamps(desc, dt_obj, "CT")
print(f"  Resultado: '{result}' (offset CT: -1h)")
print(f"  ✅ FUNCIONA" if "13:30" in result and "01:35" in result else "  ❌ ERROR")

# Caso 4: adjust_description_timestamps con string
print("\n📝 Caso 4: adjust_description_timestamps con string ISO")
desc = "Event at 14:30 and [02:35]"
dt_str = "2025-12-16 14:30:00"
print(f"  Descripción: '{desc}'")
print(f"  Base datetime: '{dt_str}' (tipo: {type(dt_str).__name__})")
result = adjust_description_timestamps(desc, dt_str, "CT")
print(f"  Resultado: '{result}' (offset CT: -1h)")
print(f"  ✅ FUNCIONA" if "13:30" in result and "01:35" in result else "  ❌ ERROR")

print("\n" + "="*80)
print("✅ TODAS LAS PRUEBAS COMPLETADAS")
print("="*80)
print("\n💡 Ahora las funciones son más robustas:")
print("  - adjust_datetime() acepta datetime o string ISO")
print("  - adjust_description_timestamps() acepta base_datetime como datetime o string")
print("  - send_to_supervisor() debería funcionar correctamente")
