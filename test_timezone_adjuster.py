"""
Script de prueba para timezone_adjuster.
Valida el parseo de timestamps en diferentes formatos.
"""
from datetime import datetime
import sys
sys.path.insert(0, r'c:\Users\hcruz.SIG\OneDrive - SIG Systems, Inc\Desktop\proyecto_app')

from utils.timezone_adjuster import adjust_description_timestamps, adjust_datetime

print("=" * 70)
print("PRUEBAS DE AJUSTE DE TIMEZONE EN DESCRIPCIONES")
print("=" * 70)
print()

# Fecha base para las pruebas
base_dt = datetime(2025, 12, 15, 14, 30, 0)

# Casos de prueba
test_cases = [
    {
        "desc": "Formato H:MM (más importante)",
        "input": "Cleaner out at 2:35",
        "tz": "MT",
        "expected": "Cleaner out at 0:35"
    },
    {
        "desc": "Formato HH:MM",
        "input": "Cleaner out at 14:35",
        "tz": "MT",
        "expected": "Cleaner out at 12:35"
    },
    {
        "desc": "Formato [H:MM] con brackets",
        "input": "Called at [2:35]",
        "tz": "MT",
        "expected": "Called at [0:35]"
    },
    {
        "desc": "Formato [HH:MM:SS]",
        "input": "Event at [14:30:00]",
        "tz": "MT",
        "expected": "Event at [12:30:00]"
    },
    {
        "desc": "Formato HH:MM:SS sin brackets",
        "input": "Timestamp 14:30:00 recorded",
        "tz": "MT",
        "expected": "Timestamp 12:30:00 recorded"
    },
    {
        "desc": "Múltiples timestamps",
        "input": "Started at 2:30, finished at 4:45",
        "tz": "MT",
        "expected": "Started at 0:30, finished at 2:45"
    },
    {
        "desc": "Timezone ET (sin cambio)",
        "input": "Cleaner out at 2:35",
        "tz": "ET",
        "expected": "Cleaner out at 2:35"
    },
    {
        "desc": "Timezone PT (-3 horas)",
        "input": "Called at 15:00",
        "tz": "PT",
        "expected": "Called at 12:00"
    },
    {
        "desc": "Formato legacy Timestamp:",
        "input": "Timestamp: 14:30 done",
        "tz": "MT",
        "expected": "[12:30] done"
    },
    {
        "desc": "Sin timestamps",
        "input": "Regular description without time",
        "tz": "MT",
        "expected": "Regular description without time"
    }
]

print("CASOS DE PRUEBA:")
print("-" * 70)

for i, test in enumerate(test_cases, 1):
    result = adjust_description_timestamps(test["input"], base_dt, test["tz"])
    status = "✅ PASS" if result == test["expected"] else "❌ FAIL"
    
    print(f"\n{i}. {test['desc']}")
    print(f"   Timezone: {test['tz']}")
    print(f"   Input:    '{test['input']}'")
    print(f"   Expected: '{test['expected']}'")
    print(f"   Result:   '{result}'")
    print(f"   Status:   {status}")

print()
print("=" * 70)
print("PRUEBA DE AJUSTE DE DATETIME")
print("=" * 70)
print()

dt_test = datetime(2025, 12, 15, 14, 30, 0)
print(f"Datetime original: {dt_test.strftime('%Y-%m-%d %H:%M:%S')}")
print()

for tz in ["ET", "CT", "MT", "MST", "PT"]:
    adjusted = adjust_datetime(dt_test, tz)
    print(f"{tz:4} -> {adjusted.strftime('%Y-%m-%d %H:%M:%S')}")

print()
print("=" * 70)
print("PRUEBA COMPLETA FINALIZADA")
print("=" * 70)
