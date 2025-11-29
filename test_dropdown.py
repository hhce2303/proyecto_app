import tkinter as tk
from tksheet import Sheet

root = tk.Tk()
root.title("Test Dropdown")

# Crear sheet simple
frame = tk.Frame(root)
frame.pack(fill="both", expand=True)

sheet = Sheet(
    frame,
    headers=["FechaHora", "Sitio", "Actividad", "Cantidad", "Camera", "Descripción"],
    height=400,
    width=1000
)
sheet.enable_bindings()
sheet.pack(fill="both", expand=True)

# Datos de prueba
sheet.set_sheet_data([
    ["2025-11-06 10:00", "Site 1", "Call", "1", "12", "Test"],
    ["2025-11-06 11:00", "", "", "0", "", ""],
])

# Configurar dropdowns SOLO en columnas específicas
sites = ["Site 1", "Site 2", "Site 3"]
activities = ["Call", "Call Report", "Meeting"]

print("Método dropdown signature:")
import inspect
print(inspect.signature(sheet.dropdown))

# SINTAXIS CORRECTA: usar rangos de columnas
# sheet.dropdown(row_start, col_start, row_end, col_end, values=[...])
print("\n--- Intentando configurar dropdowns con rangos ---")

# Configurar dropdown PARA TODA LA COLUMNA 1 (Sitio) - todas las filas
try:
    # Sintaxis: desde fila 0, columna 1, hasta fila 1000, columna 1
    result1 = sheet.dropdown(0, 1, sheet.total_rows(), 1, values=sites)
    print(f"✅ Dropdown en COLUMNA 1 (Sitio): Success")
except Exception as e:
    print(f"❌ Error columna 1: {type(e).__name__}: {e}")

# Configurar dropdown PARA TODA LA COLUMNA 2 (Actividad)
try:
    result2 = sheet.dropdown(0, 2, sheet.total_rows(), 2, values=activities)
    print(f"✅ Dropdown en COLUMNA 2 (Actividad): Success")
except Exception as e:
    print(f"❌ Error columna 2: {type(e).__name__}: {e}")

print("\n--- Testing complete, close window to exit ---")

root.mainloop()
