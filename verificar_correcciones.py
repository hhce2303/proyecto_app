# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que las correcciones funcionan
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("="*80)
print("VERIFICACIÓN DE CORRECCIONES")
print("="*80)

# Verificar Problema 1: create_event acepta fecha_hora
print("\n✅ Problema 1: Parámetro fecha_hora en create_event")
print("-" * 80)

# Importar el modelo
from models import daily_model
from datetime import datetime

# Verificar firma del método
import inspect
signature = inspect.signature(daily_model.create_event)
params = list(signature.parameters.keys())

print(f"Parámetros de create_event: {params}")

if 'fecha_hora' in params:
    print("✅ CORRECTO: fecha_hora está en los parámetros")
    
    # Verificar si tiene default
    param_obj = signature.parameters['fecha_hora']
    if param_obj.default != inspect.Parameter.empty:
        print(f"✅ CORRECTO: fecha_hora tiene default = {param_obj.default}")
    else:
        print("⚠️ ADVERTENCIA: fecha_hora no tiene default, será obligatorio")
else:
    print("❌ ERROR: fecha_hora NO está en los parámetros")

# Verificar controller
print("\n✅ Controller: Verificar DailyController")
print("-" * 80)

from controllers.daily_controller import DailyController

signature_controller = inspect.signature(DailyController.create_event)
params_controller = list(signature_controller.parameters.keys())

print(f"Parámetros de DailyController.create_event: {params_controller}")

if 'fecha_hora' in params_controller:
    print("✅ CORRECTO: fecha_hora está en el controller")
else:
    print("❌ ERROR: fecha_hora NO está en el controller")

print("\n" + "="*80)
print("RESULTADO:")
print("="*80)

if 'fecha_hora' in params and 'fecha_hora' in params_controller:
    print("✅ Problema 1 SOLUCIONADO - create_event ahora acepta fecha_hora personalizada")
else:
    print("❌ Problema 1 NO SOLUCIONADO - Revisa los archivos")

print("\n💡 Sobre Problema 2 (FilteredCombobox):")
print("   - Verifica que puedas hacer click en el combobox")
print("   - Intenta presionar Delete/Backspace primero")
print("   - Luego intenta escribir")
print("   - Si no funciona, reporta exactamente qué sucede")
print()
