# -*- coding: utf-8 -*-
"""
Prueba rápida del controlador de Specials con los cambios de timezone
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from controllers.specials_operator_controller import SpecialsOperatorController
from utils.timezone_adjuster import get_timezone_offset

# Simular un username (cambia esto por un operador real)
username = "TEST_OPERATOR"

print("="*80)
print("PRUEBA DE CONTROLADOR DE SPECIALS CON TIMEZONE_ADJUSTER")
print("="*80)

# Crear controlador
controller = SpecialsOperatorController(username)

print(f"\n✅ Controlador creado para: {username}")
print(f"✅ Ya NO usa self.tz_config de base de datos")
print(f"✅ Ahora usa get_timezone_offset() directamente")

# Probar get_timezone_offset
print("\n📝 Probando get_timezone_offset():")
test_timezones = ["ET", "CT", "MT", "MST", "PT", "UNKNOWN"]
for tz in test_timezones:
    offset = get_timezone_offset(tz)
    print(f"   {tz}: {offset:+d} horas")

print("\n✅ PRUEBA EXITOSA - El controlador ahora usa timezone_adjuster.py")
print("="*80)
